"""Shared-recognition workflow for the optional virtual gamepad."""

from ..adapters.gamepad import open_gamepad
from ..bundles import load_active_bundle
from ..recognition import new_smoothing_state, recognize_frame


def _live_frames(config):
    import cv2
    import mediapipe as mp

    camera, hands_config = config["CAMERA"], config["MEDIAPIPE"]
    capture = cv2.VideoCapture(camera["camera_index"])
    for property_id, value in ((cv2.CAP_PROP_FRAME_WIDTH, camera.get("width")), (cv2.CAP_PROP_FRAME_HEIGHT, camera.get("height"))):
        if value is not None:
            capture.set(property_id, value)
    try:
        with mp.solutions.hands.Hands(
            max_num_hands=hands_config["max_num_hands"],
            min_detection_confidence=hands_config["min_detection_confidence"],
            min_tracking_confidence=hands_config["min_tracking_confidence"],
            model_complexity=hands_config.get("model_complexity", 1),
        ) as hands:
            while True:
                valid, frame = capture.read()
                if not valid:
                    return
                if camera.get("flip_horizontal", False):
                    frame = cv2.flip(frame, 1)
                results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                yield tuple((side.classification[0].label.lower(), landmarks.landmark) for landmarks, side in zip(results.multi_hand_landmarks or (), results.multi_handedness or ()))
    finally:
        capture.release()
        cv2.destroyAllWindows()


def run(config, frames=None, artifact_loader=None, adapter_factory=open_gamepad):
    """Validate recognition, then neutralize controls on every unsafe exit."""
    model, scaler, manifest = load_active_bundle(config["PATHS"]["bundles"], artifact_loader)
    histories = new_smoothing_state(config["INFERENCE"]["smoothing_window"])
    adapter = adapter_factory(config)
    outcomes = []
    try:
        for detections in frames if frames is not None else _live_frames(config):
            result = recognize_frame(detections, model, scaler, manifest["labels"].__getitem__, config["INFERENCE"]["prediction_threshold"], histories)
            adapter.apply(result)
            outcomes.append(result)
        return tuple(outcomes)
    finally:
        adapter.neutralize()
