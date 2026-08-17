"""Validated visual inference with lazy camera dependencies."""

from ..bundles import load_active_bundle
from ..recognition import new_smoothing_state, recognize_frame


def _live_run(config, model, scaler, decoder, histories, camera_factory=None):
    import cv2
    import mediapipe as mp

    camera = config["CAMERA"]
    visualization = config.get("VISUALIZATION", {})
    hands_config = config["MEDIAPIPE"]
    capture = (camera_factory or cv2.VideoCapture)(camera["camera_index"])
    for property_id, value in ((cv2.CAP_PROP_FRAME_WIDTH, camera.get("width")), (cv2.CAP_PROP_FRAME_HEIGHT, camera.get("height"))):
        if value is not None:
            capture.set(property_id, value)
    window = config["INFERENCE"]["smoothing_window"]
    print(f"Suavizado activado con ventana de {window} frames por mano" if window else "Suavizado desactivado")
    print("Iniciando detección en tiempo real con soporte para dos manos...")
    print("Presiona ESC para salir")
    mp_hands = mp.solutions.hands
    try:
        with mp_hands.Hands(
            max_num_hands=hands_config["max_num_hands"],
            min_detection_confidence=hands_config["min_detection_confidence"],
            min_tracking_confidence=hands_config["min_tracking_confidence"],
            model_complexity=hands_config.get("model_complexity", 1),
        ) as hands:
            while True:
                valid, frame = capture.read()
                if not valid:
                    break
                if camera.get("flip_horizontal", False):
                    frame = cv2.flip(frame, 1)
                results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pairs = tuple(zip(results.multi_hand_landmarks or (), results.multi_handedness or ()))
                detections = tuple((side.classification[0].label.lower(), landmarks.landmark) for landmarks, side in pairs)
                outcomes = recognize_frame(detections, model, scaler, decoder, config["INFERENCE"]["prediction_threshold"], histories)
                if visualization.get("show_landmarks", True):
                    for landmarks, side in pairs:
                        color = (0, 255, 0) if side.classification[0].label.lower() == "left" else (255, 0, 255)
                        mp.solutions.drawing_utils.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS, mp.solutions.drawing_utils.DrawingSpec(color=color, thickness=2, circle_radius=2), mp.solutions.drawing_utils.DrawingSpec(color=color, thickness=2))
                if visualization.get("show_gesture_label", True):
                    for y, hand, prefix, color in ((30, "left", "Izq", (0, 255, 0)), (65, "right", "Der", (255, 0, 255))):
                        label, confidence = outcomes[hand]
                        text = f"{prefix}: {label or '-'}"
                        if label and visualization.get("show_confidence", False):
                            text += f" ({confidence:.2f})"
                        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color if label else (100, 100, 100), 2, cv2.LINE_AA)
                cv2.imshow(visualization.get("window_title", "Detección de Gestos"), frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
    finally:
        capture.release()
        cv2.destroyAllWindows()
        print("Detección finalizada")


def run(config, frames=None, artifact_loader=None, camera_factory=None):
    """Validate the selected bundle before consuming fake or live frames."""
    model, scaler, manifest = load_active_bundle(config["PATHS"]["bundles"], artifact_loader)
    histories = new_smoothing_state(config["INFERENCE"]["smoothing_window"])
    decoder = manifest["labels"].__getitem__
    if frames is not None:
        return tuple(recognize_frame(frame, model, scaler, decoder, config["INFERENCE"]["prediction_threshold"], histories) for frame in frames)
    return _live_run(config, model, scaler, decoder, histories, camera_factory)
