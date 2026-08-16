"""
Script 0: Creación de Dataset de Gestos
Captura gestos de manos usando MediaPipe y los guarda en un CSV
"""


def _legacy_main():
    import cv2
    import mediapipe as mp
    import numpy as np
    import pandas as pd
    import yaml
    import os

    # Cargar configuración
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Configuración de MediaPipe
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    # Configuración de cámara
    camera_index = config['CAMERA']['camera_index']
    cap = cv2.VideoCapture(camera_index)

    # Configuración de MediaPipe Hands
    hands_config = config['MEDIAPIPE']
    hands = mp_hands.Hands(
        static_image_mode=hands_config['static_image_mode'],
        max_num_hands=hands_config['max_num_hands'],
        min_detection_confidence=hands_config['min_detection_confidence'],
        min_tracking_confidence=hands_config['min_tracking_confidence'],
        model_complexity=hands_config['model_complexity']
    )

    # Mapeo de teclas a gestos desde configuración
    gesture_capture = config['GESTURE_CAPTURE']
    gestures = {}
    for gesture_name, key_char in gesture_capture.items():
        if gesture_name != 'exit' and key_char is not None:
            if key_char == 'ESC':
                gestures[27] = gesture_name  # ESC key
            else:
                gestures[ord(key_char)] = gesture_name

    data, labels = [], []

    print("=" * 60)
    print("CAPTURA DE DATASET DE GESTOS")
    print("=" * 60)
    print("\nInstrucciones:")
    print("- Presiona las teclas correspondientes mientras haces el gesto")
    print("- Presiona ESC para finalizar la captura")
    print("\nMapeo de teclas:")
    for key, gesture in sorted(gestures.items(), key=lambda x: x[1]):
        if isinstance(key, int) and key != 27:
            print(f"  {chr(key).upper()}: {gesture}")
    print("=" * 60)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo leer el frame de la cámara")
                break

            # Voltear imagen si está configurado
            if config['CAMERA']['flip_horizontal']:
                frame = cv2.flip(frame, 1)

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(img)

            # Dibujar landmarks si se detecta mano
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    if config['VISUALIZATION']['show_landmarks']:
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                            mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                        )

                    # Extraer coordenadas
                    coords = np.array([[point.x, point.y] for point in hand_landmarks.landmark])

                    # Normalizar respecto a muñeca si está configurado
                    if config['PREPROCESSING']['normalize_to_wrist']:
                        coords = coords - coords[0]

                    features = coords.flatten()

                    # Mostrar instrucciones en pantalla
                    cv2.putText(frame, "Presiona tecla para capturar gesto", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"Muestras capturadas: {len(data)}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Captura de Dataset", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in gestures:
                if results.multi_hand_landmarks:
                    data.append(features)
                    labels.append(gestures[key])
                    print(f"[{len(data)}] Guardada muestra para gesto: {gestures[key]}")
                else:
                    print("Advertencia: No se detecta mano. No se guardó la muestra.")
            elif key == 27:  # ESC
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()

    # Guardar dataset
    if len(data) > 0:
        # Crear directorio de salida si no existe
        output_path = config['PREPROCESSING']['output_csv']
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df = pd.DataFrame(data)
        df['label'] = labels
        df.to_csv(output_path, index=False)

        print("\n" + "=" * 60)
        print(f"Dataset guardado exitosamente en: {output_path}")
        print(f"Total de muestras: {len(data)}")
        print(f"Gestos únicos: {len(set(labels))}")
        print("=" * 60)

        # Mostrar distribución de gestos
        print("\nDistribución de gestos:")
        gesture_counts = pd.Series(labels).value_counts().sort_index()
        for gesture, count in gesture_counts.items():
            print(f"  {gesture}: {count} muestras")
    else:
        print("\nAdvertencia: No se capturaron muestras. El dataset no se guardó.")


def main():
    """Delegate the legacy entrypoint to the capture workflow."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from gesture_vision.config import load_config
    from gesture_vision.workflows.capture import run

    return run(load_config(root / "config" / "config.yaml"))


if __name__ == "__main__":
    main()
