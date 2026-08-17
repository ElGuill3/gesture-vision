"""Session-grouped model training with lazy ML imports."""

import sys
from pathlib import Path
from uuid import uuid4

from ..bundles import promote_bundle
from ..features import FEATURE_DIMENSION
from ..sessions import partition_sessions


def _default_fitter(groups, config):
    import joblib
    import sklearn
    import tensorflow as tf
    from sklearn.preprocessing import StandardScaler

    training = config.get("TRAINING", {})
    labels = tuple(sorted({sample["label"] for group in groups.values() for session in group for sample in session["samples"]}))
    encoded = {label: index for index, label in enumerate(labels)}
    samples = {name: [sample for session in group for sample in session["samples"]] for name, group in groups.items()}
    scaler = StandardScaler().fit([sample["features"] for sample in samples["train"]])
    model = tf.keras.Sequential([tf.keras.layers.Input((FEATURE_DIMENSION,)), tf.keras.layers.Dense(training.get("hidden_units", 128), activation="relu"), tf.keras.layers.Dense(len(labels), activation="softmax")])
    model.compile(optimizer=tf.keras.optimizers.Adam(training.get("learning_rate", 0.003)), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(scaler.transform([sample["features"] for sample in samples["train"]]), [encoded[sample["label"]] for sample in samples["train"]], epochs=training.get("epochs", 100), batch_size=training.get("batch_size", 32), validation_data=(scaler.transform([sample["features"] for sample in samples["validation"]]), [encoded[sample["label"]] for sample in samples["validation"]]), verbose=1)

    def write_artifacts(directory):
        model.save(Path(directory) / "model.keras")
        joblib.dump(scaler, Path(directory) / "scaler.joblib")

    return labels, write_artifacts, {"python": sys.version.split()[0], "tensorflow": tf.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__}


def run(config, session_paths=None, fitter=None, artifact_loader=None):
    """Validate session partitions before fitting or publishing anything."""
    paths = tuple(session_paths) if session_paths is not None else tuple(sorted(Path(config["PATHS"]["sessions"]).glob("*.json")))
    seed = config.get("TRAINING", {}).get("split_seed", 42)
    groups = partition_sessions(paths, seed=seed)
    labels, write_artifacts, versions = (fitter or _default_fitter)(groups, config)
    membership = {name: [session["session_id"] for session in group] for name, group in groups.items()}
    return promote_bundle(config["PATHS"]["bundles"], uuid4().hex, labels, seed, membership, write_artifacts, artifact_loader, versions)
