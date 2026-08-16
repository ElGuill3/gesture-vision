"""Configuration loading without import-time third-party dependencies."""

from copy import deepcopy
from importlib.resources import files
from pathlib import Path


def _yaml_mapping(text, source):
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("PyYAML is required to load GestureVision configuration") from error
    value = yaml.safe_load(text) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Configuration {source} must contain a mapping")
    return value


def _merge(base, overlay):
    result = deepcopy(base)
    for key, value in overlay.items():
        result[key] = _merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def _default_root():
    root = Path(__file__).resolve().parents[2]
    return root if (root / "pyproject.toml").is_file() else Path.cwd()


def _config_base(path):
    return path.parent.parent if path.name == "config.yaml" and path.parent.name == "config" else path.parent


def load_config(config_path=None, cli_overrides=None, root=None):
    """Merge packaged defaults, an optional YAML overlay, then explicit overrides."""
    config = _yaml_mapping(files("gesture_vision").joinpath("defaults.yaml").read_text(), "package defaults")
    path = Path(config_path).expanduser().resolve() if config_path else None
    if path:
        config = _merge(config, _yaml_mapping(path.read_text(encoding="utf-8"), path))
    if cli_overrides:
        config = _merge(config, cli_overrides)
    base = _config_base(path) if path else _default_root()
    root_value = root if root is not None else config["PATHS"].get("root", ".")
    config_root = Path(root_value).expanduser()
    config_root = (base / config_root if not config_root.is_absolute() else config_root).resolve()
    paths = config["PATHS"]
    paths["root"] = config_root
    for key, value in tuple(paths.items()):
        if key != "root" and isinstance(value, str):
            path_value = Path(value).expanduser()
            paths[key] = (config_root / path_value if not path_value.is_absolute() else path_value).resolve()
    return config
