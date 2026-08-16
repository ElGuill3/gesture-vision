"""Live capture workflow with lazy vision imports."""

from ..sessions import CaptureSession


def _gesture_keys(config):
    return {
        27 if key == "ESC" else ord(key): label
        for label, key in config.get("GESTURE_CAPTURE", {}).items()
        if label != "exit" and key is not None
    }


def _live_frames(config):
    import cv2
    import mediapipe as mp

    camera = config["CAMERA"]
    hands_config = config["MEDIAPIPE"]
    gestures = _gesture_keys(config)
    mp_hands = mp.solutions.hands
    drawing = mp.solutions.drawing_utils
    capture = cv2.VideoCapture(camera["camera_index"])
    for setting, value in ((cv2.CAP_PROP_FRAME_WIDTH, camera.get("width")), (cv2.CAP_PROP_FRAME_HEIGHT, camera.get("height"))):
        if value is not None:
            capture.set(setting, value)
    print("=" * 60)
    print("CAPTURA DE DATASET DE GESTOS")
    print("=" * 60)
    print("\nInstrucciones:")
    print("- Presiona las teclas correspondientes mientras haces el gesto")
    print("- Presiona ESC para finalizar la captura")
    print("\nMapeo de teclas:")
    for key, label in sorted(gestures.items(), key=lambda item: item[1]):
        print(f"  {chr(key).upper()}: {label}")
    print("=" * 60)
    try:
        with mp_hands.Hands(
            static_image_mode=hands_config.get("static_image_mode", False),
            max_num_hands=hands_config["max_num_hands"],
            min_detection_confidence=hands_config["min_detection_confidence"],
            min_tracking_confidence=hands_config["min_tracking_confidence"],
            model_complexity=hands_config.get("model_complexity", 1),
        ) as hands:
            frame_id = 0
            while True:
                valid, frame = capture.read()
                if not valid:
                    raise RuntimeError("Error: No se pudo leer el frame de la cámara")
                if camera.get("flip_horizontal", False):
                    frame = cv2.flip(frame, 1)
                results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                landmarks = results.multi_hand_landmarks or ()
                handedness = results.multi_handedness or ()
                detections = tuple(
                    (classification.classification[0].label.lower(), hand.landmark)
                    for hand, classification in zip(landmarks, handedness)
                )
                for hand in landmarks:
                    drawing.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                cv2.putText(frame, "Presiona tecla para capturar gesto", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Captura de Dataset", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in gestures:
                    if detections:
                        yield frame_id, gestures[key], detections
                    else:
                        print("Advertencia: No se detecta mano. No se guardó la muestra.")
                elif key == 27:
                    return
                frame_id += 1
    finally:
        capture.release()
        cv2.destroyAllWindows()


def run(config, frames=None):
    """Capture fake or live frames and publish only a completed non-empty session."""
    session = CaptureSession(config["PATHS"]["sessions"])
    try:
        for frame_id, label, detections in frames if frames is not None else _live_frames(config):
            accepted = session.record_frame(frame_id, label, detections)
            if accepted:
                print(f"[{session.sample_count}] Guardada muestra para gesto: {label}")
    except KeyboardInterrupt:
        return None
    result = session.finalize()
    if result is None:
        print("\nAdvertencia: No se capturaron muestras. El dataset no se guardó.")
    return result
