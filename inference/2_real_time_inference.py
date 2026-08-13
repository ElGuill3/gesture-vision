"""
Script 2: Inferencia en Tiempo Real
Detecta gestos en tiempo real usando la cámara y muestra el resultado
Soporta detección de dos manos simultáneas
"""


def main():
    import cv2
    import mediapipe as mp
    import numpy as np
    import joblib
    from tensorflow.keras.models import load_model
    import yaml
    import os
    from collections import deque, Counter

    # Cargar configuración
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Cargar modelo y objetos de preprocesamiento
    print("Cargando modelo y utilidades...")
    model_path = config['INFERENCE']['model_path']
    scaler_path = config['INFERENCE']['scaler_path']
    label_encoder_path = config['INFERENCE']['label_encoder_path']

    if not all(os.path.exists(p) for p in [model_path, scaler_path, label_encoder_path]):
        raise FileNotFoundError("No se encontraron los archivos del modelo. Ejecuta primero el entrenamiento.")

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)
    label_encoder = joblib.load(label_encoder_path)

    # Inicializa MediaPipe Hands
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    # Configuración de MediaPipe
    hands_config = config['MEDIAPIPE']
    hands = mp_hands.Hands(
        max_num_hands=hands_config['max_num_hands'],
        min_detection_confidence=hands_config['min_detection_confidence'],
        min_tracking_confidence=hands_config['min_tracking_confidence'],
        model_complexity=hands_config['model_complexity']
    )

    # Configuración de cámara
    camera_index = config['CAMERA']['camera_index']
    cap = cv2.VideoCapture(camera_index)

    # Suavizado de predicciones separado por mano
    smoothing_window = config['INFERENCE']['smoothing_window']
    if smoothing_window > 0:
        prediction_buffer_left = deque(maxlen=smoothing_window)
        prediction_buffer_right = deque(maxlen=smoothing_window)
        print(f"Suavizado activado con ventana de {smoothing_window} frames por mano")
    else:
        prediction_buffer_left = None
        prediction_buffer_right = None
        print("Suavizado desactivado")

    print("Iniciando detección en tiempo real con soporte para dos manos...")
    print("Presiona ESC para salir")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Voltear imagen si está configurado
            if config['CAMERA']['flip_horizontal']:
                frame = cv2.flip(frame, 1)

            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            # Diccionarios para almacenar gestos detectados por mano
            gestures_detected = {
                'Left': None,
                'Right': None
            }
            confidences = {
                'Left': 0.0,
                'Right': 0.0
            }

            # Procesar todas las manos detectadas
            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    hand_label = handedness.classification[0].label  # "Left" o "Right"

                    # Extraer coordenadas normalizadas X,Y de landmarks
                    coords = np.array([[lm.x, lm.y] for lm in hand_landmarks.landmark])

                    # Normalizar respecto a la muñeca si está configurado
                    if config['PREPROCESSING']['normalize_to_wrist']:
                        coords = coords - coords[0]

                    features = coords.flatten().reshape(1, -1)
                    features = scaler.transform(features)

                    # Predecir el gesto
                    pred_probs = model.predict(features, verbose=0)
                    pred_class = np.argmax(pred_probs)
                    confidence = float(pred_probs[0][pred_class])

                    # Solo considerar el gesto si la confianza supera el umbral
                    if confidence >= config['INFERENCE']['prediction_threshold']:
                        detected_gesture = label_encoder.inverse_transform([pred_class])[0]

                        # Suavizado de predicciones por mano
                        buffer = prediction_buffer_left if hand_label == 'Left' else prediction_buffer_right
                        if buffer is not None:
                            buffer.append(pred_class)
                            most_common = Counter(buffer).most_common(1)[0][0]
                            detected_gesture = label_encoder.inverse_transform([most_common])[0]

                        gestures_detected[hand_label] = detected_gesture
                        confidences[hand_label] = confidence
                    else:
                        gestures_detected[hand_label] = None
                        confidences[hand_label] = confidence

                    # Dibujar landmarks si está configurado
                    if config['VISUALIZATION']['show_landmarks']:
                        # Color diferente para cada mano
                        color_landmarks = (0, 255, 0) if hand_label == 'Left' else (255, 0, 255)  # Verde para izquierda, Magenta para derecha
                        color_connections = (0, 255, 0) if hand_label == 'Left' else (255, 0, 255)

                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=color_landmarks, thickness=2, circle_radius=2),
                            mp_drawing.DrawingSpec(color=color_connections, thickness=2)
                        )

            # Mostrar información en pantalla
            if config['VISUALIZATION']['show_gesture_label']:
                y_offset = 30
                # Mano izquierda
                if gestures_detected['Left'] is not None:
                    text = f'Izq: {gestures_detected["Left"]}'
                    if config['VISUALIZATION']['show_confidence']:
                        text += f' ({confidences["Left"]:.2f})'
                    color = (0, 255, 0)  # Verde
                else:
                    text = 'Izq: -'
                    color = (100, 100, 100)  # Gris

                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

                # Mano derecha
                y_offset += 35
                if gestures_detected['Right'] is not None:
                    text = f'Der: {gestures_detected["Right"]}'
                    if config['VISUALIZATION']['show_confidence']:
                        text += f' ({confidences["Right"]:.2f})'
                    color = (255, 0, 255)  # Magenta
                else:
                    text = 'Der: -'
                    color = (100, 100, 100)  # Gris

                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

            window_title = config['VISUALIZATION']['window_title']
            cv2.imshow(window_title, frame)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC para salir
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        print("Detección finalizada")


if __name__ == "__main__":
    main()
