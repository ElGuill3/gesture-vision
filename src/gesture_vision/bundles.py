"""Validated, immutable model bundles and atomic portable selection."""

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .features import FEATURE_DIMENSION, FEATURE_SCHEMA

_ARTIFACTS = ("model.keras", "scaler.joblib")
_VERSION_KEYS = ("python", "tensorflow", "scikit_learn", "joblib")
_BUNDLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as file:
            json.dump(value, file, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _labels_hash(labels):
    return hashlib.sha256(json.dumps(list(labels), separators=(",", ":")).encode()).hexdigest()


def _manifest(bundle_id, labels, groups, directory, versions):
    labels = list(labels)
    if any(not (Path(directory) / name).is_file() for name in _ARTIFACTS):
        raise ValueError("Bundle artifacts are incomplete")
    return {
        "format_version": 1,
        "bundle_id": bundle_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_schema": FEATURE_SCHEMA,
        "input_dimension": FEATURE_DIMENSION,
        "output_dimension": len(labels),
        "labels": labels,
        "labels_sha256": _labels_hash(labels),
        "artifacts": {name: {"path": name, "sha256": _sha256(Path(directory) / name)} for name in _ARTIFACTS},
        "split": {"seed": groups["seed"], "groups": groups["groups"]},
        "versions": versions,
    }


def _dimension(shape):
    if isinstance(shape, list):
        shape = shape[0]
    try:
        return int(shape[-1])
    except (IndexError, TypeError, ValueError) as error:
        raise ValueError("Model shape is invalid") from error


def _load_artifacts(model_path, scaler_path):
    import joblib
    import tensorflow as tf

    return tf.keras.models.load_model(model_path), joblib.load(scaler_path)


def validate_bundle(directory, artifact_loader=None, expected_bundle_id=None):
    """Reload and validate a complete bundle before it can be selected."""
    directory = Path(directory)
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid bundle manifest in {directory}") from error
    required = {"format_version", "bundle_id", "created_at", "feature_schema", "input_dimension", "output_dimension", "labels", "labels_sha256", "artifacts", "split", "versions"}
    if not isinstance(manifest, dict) or required - manifest.keys() or manifest["format_version"] != 1:
        raise ValueError("Bundle manifest is incomplete or unsupported")
    bundle_id = manifest["bundle_id"]
    if not isinstance(bundle_id, str) or not _BUNDLE_ID.fullmatch(bundle_id) or expected_bundle_id not in (None, bundle_id):
        raise ValueError("Bundle manifest has an invalid bundle_id")
    try:
        created_at = datetime.fromisoformat(manifest["created_at"])
    except (TypeError, ValueError) as error:
        raise ValueError("Bundle manifest has an invalid created_at") from error
    if created_at.utcoffset() != timezone.utc.utcoffset(created_at) or manifest["feature_schema"] != FEATURE_SCHEMA or manifest["input_dimension"] != FEATURE_DIMENSION:
        raise ValueError("Bundle manifest is incompatible with the feature contract")
    labels = manifest["labels"]
    if not isinstance(labels, list) or not labels or any(not isinstance(label, str) or not label for label in labels) or len(labels) != len(set(labels)) or manifest["output_dimension"] != len(labels) or manifest["labels_sha256"] != _labels_hash(labels):
        raise ValueError("Bundle manifest has invalid labels")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != set(_ARTIFACTS):
        raise ValueError("Bundle manifest has invalid artifacts")
    for name in _ARTIFACTS:
        artifact = artifacts[name]
        if not isinstance(artifact, dict) or artifact.get("path") != name or not (directory / name).is_file() or not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) or _sha256(directory / name) != artifact["sha256"]:
            raise ValueError(f"Bundle artifact {name} is missing or has an invalid checksum")
    split = manifest["split"]
    groups = split.get("groups") if isinstance(split, dict) else None
    members = [member for name in ("train", "validation", "test") for member in groups.get(name, ())] if isinstance(groups, dict) else []
    if not isinstance(split, dict) or isinstance(split.get("seed"), bool) or not isinstance(split.get("seed"), int) or set(groups or ()) != {"train", "validation", "test"} or any(not isinstance(groups[name], list) or not groups[name] for name in groups or ()) or not members or len(members) != len(set(members)) or any(not isinstance(member, str) or not member for member in members):
        raise ValueError("Bundle manifest has invalid split membership")
    versions = manifest["versions"]
    if not isinstance(versions, dict) or set(_VERSION_KEYS) - versions.keys() or any(not isinstance(versions[key], str) or not versions[key] for key in _VERSION_KEYS):
        raise ValueError("Bundle manifest has invalid version metadata")
    model, scaler = (artifact_loader or _load_artifacts)(directory / "model.keras", directory / "scaler.joblib")
    if _dimension(model.input_shape) != FEATURE_DIMENSION or _dimension(model.output_shape) != len(labels) or getattr(scaler, "n_features_in_", None) != FEATURE_DIMENSION:
        raise ValueError("Bundle artifacts are dimension-incompatible")
    return model, scaler, manifest


def _selection(root):
    path = Path(root) / "selection.json"
    if not path.exists():
        return {"format_version": 1, "active": None, "previous": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Bundle selector is invalid") from error
    if not isinstance(value, dict) or value.get("format_version") != 1 or set(value) != {"format_version", "active", "previous"} or any(value[key] is not None and (not isinstance(value[key], str) or not _BUNDLE_ID.fullmatch(value[key])) for key in ("active", "previous")):
        raise ValueError("Bundle selector is invalid")
    return value


def _validate_selected(root, selection, artifact_loader):
    for name in ("active", "previous"):
        if selection[name] is not None:
            validate_bundle(Path(root) / selection[name], artifact_loader, selection[name])


def promote_bundle(root, bundle_id, labels, split_seed, split_groups, write_artifacts, artifact_loader=None, versions=None):
    """Stage, reload-validate, and atomically select a new immutable bundle."""
    if not isinstance(bundle_id, str) or not _BUNDLE_ID.fullmatch(bundle_id):
        raise ValueError("Bundle ID is invalid")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    selection = _selection(root)
    _validate_selected(root, selection, artifact_loader)
    final = root / bundle_id
    if final.exists():
        raise FileExistsError(f"Bundle already exists: {bundle_id}")
    stage = root / f".{bundle_id}.{uuid4().hex}.stage"
    stage.mkdir()
    try:
        write_artifacts(stage)
        manifest = _manifest(bundle_id, labels, {"seed": split_seed, "groups": split_groups}, stage, versions or {"python": sys.version.split()[0], "tensorflow": "unknown", "scikit_learn": "unknown", "joblib": "unknown"})
        _atomic_json(stage / "manifest.json", manifest)
        validate_bundle(stage, artifact_loader, bundle_id)
        os.replace(stage, final)
        _atomic_json(root / "selection.json", {"format_version": 1, "active": bundle_id, "previous": selection["active"]})
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return final


def rollback_bundle(root, artifact_loader=None):
    """Atomically restore the validated previous bundle."""
    root = Path(root)
    selection = _selection(root)
    if selection["active"] is None or selection["previous"] is None:
        raise ValueError("No previous bundle is available for rollback")
    _validate_selected(root, selection, artifact_loader)
    restored = {"format_version": 1, "active": selection["previous"], "previous": selection["active"]}
    _atomic_json(root / "selection.json", restored)
    return root / restored["active"]
