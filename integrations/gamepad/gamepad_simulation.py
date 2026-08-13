"""
Script 3: Simulación de Gamepad Virtual
Detecta gestos en tiempo real y los mapea a un gamepad virtual Xbox 360
Soporta detección de dos manos simultáneas con mapeo fijo por mano
"""
import cv2
import mediapipe as mp
import numpy as np
import joblib
from tensorflow.keras.models import load_model
import vgamepad as vg
import yaml
import os
import sys
from collections import deque, Counter

# Agregar directorio raíz al path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Cargar configuración
config_path = os.path.join(project_root, 'config', 'config.yaml')
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

# Crea instancia de gamepad virtual (XInput Xbox 360)
gamepad = vg.VX360Gamepad()

# Mapear nombres de botones de configuración a constantes de vgamepad
BUTTON_MAP = {
    'XUSB_GAMEPAD_DPAD_UP': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    'XUSB_GAMEPAD_DPAD_DOWN': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    'XUSB_GAMEPAD_DPAD_LEFT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    'XUSB_GAMEPAD_DPAD_RIGHT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    'XUSB_GAMEPAD_A': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    'XUSB_GAMEPAD_B': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    'XUSB_GAMEPAD_X': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    'XUSB_GAMEPAD_Y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    'XUSB_GAMEPAD_LEFT_SHOULDER': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    'XUSB_GAMEPAD_RIGHT_SHOULDER': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
}

# Construir mapeo de gestos a botones D-pad (solo mano izquierda)
gesture_to_dpad = {}
for gesture, button_str in config['GAMEPAD']['gesture_to_dpad'].items():
    if button_str is None:
        gesture_to_dpad[gesture] = 0
    elif ',' in button_str:  # Diagonales (múltiples botones)
        buttons = [BUTTON_MAP[b.strip()] for b in button_str.split(',')]
        gesture_to_dpad[gesture] = buttons
    else:
        gesture_to_dpad[gesture] = BUTTON_MAP.get(button_str, 0)

# Construir mapeo de gestos a botones de acción (solo mano derecha)
gesture_to_action_buttons = {}
for gesture, button_str in config['GAMEPAD']['gesture_to_action_buttons'].items():
    gesture_to_action_buttons[gesture] = BUTTON_MAP.get(button_str, 0)

# Construir mapeo de gestos a botones de hombro
gesture_to_shoulder_buttons = {}
for gesture, button_str in config['GAMEPAD']['gesture_to_shoulder_buttons'].items():
    gesture_to_shoulder_buttons[gesture] = BUTTON_MAP.get(button_str, 0)

# Construir mapeo de gestos a gatillos
gesture_to_triggers = {}
for gesture, trigger_str in config['GAMEPAD']['gesture_to_triggers'].items():
    gesture_to_triggers[gesture] = trigger_str

# Conjuntos de botones para manejar estados
dpad_buttons = {
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
}

action_buttons = {
    vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
}

shoulder_buttons = {
    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
}

# Estado actual de botones presionados por mano
botones_izquierda = set()  # D-Pad, LB, LT
botones_derecha = set()    # A/B/X/Y, RB, RT

def actualizar_dpad(nueva_direccion):
    """Actualiza el estado del D-pad (solo mano izquierda)"""
    global botones_izquierda

    # Si nueva_direccion es 0 o None, liberamos todos los botones del D-pad
    if nueva_direccion == 0 or nueva_direccion is None:
        for boton in botones_izquierda.copy():
            if boton in dpad_buttons:
                gamepad.release_button(boton)
                gamepad.update()
                botones_izquierda.remove(boton)
    elif isinstance(nueva_direccion, list):
        # Diagonales: lista de botones
        for boton in botones_izquierda.copy():
            if boton in dpad_buttons and boton not in nueva_direccion:
                gamepad.release_button(boton)
                gamepad.update()
                botones_izquierda.remove(boton)
        for boton in nueva_direccion:
            if boton not in botones_izquierda:
                gamepad.press_button(boton)
                gamepad.update()
                botones_izquierda.add(boton)
    else:
        # Dirección única
        for boton in botones_izquierda.copy():
            if boton in dpad_buttons and boton != nueva_direccion:
                gamepad.release_button(boton)
                gamepad.update()
                botones_izquierda.remove(boton)
        if nueva_direccion not in botones_izquierda:
            gamepad.press_button(nueva_direccion)
            gamepad.update()
            botones_izquierda.add(nueva_direccion)

def actualizar_botones_accion(nuevo_boton):
    """Actualiza el estado de botones A/B/X/Y (solo mano derecha)"""
    global botones_derecha

    if nuevo_boton == 0 or nuevo_boton is None:
        for boton in botones_derecha.copy():
            if boton in action_buttons:
                gamepad.release_button(boton)
                gamepad.update()
                botones_derecha.remove(boton)
    else:
        for boton in botones_derecha.copy():
            if boton in action_buttons and boton != nuevo_boton:
                gamepad.release_button(boton)
                gamepad.update()
                botones_derecha.remove(boton)
        if nuevo_boton not in botones_derecha:
            gamepad.press_button(nuevo_boton)
            gamepad.update()
            botones_derecha.add(nuevo_boton)

def actualizar_boton_hombro(boton, activo):
    """Actualiza el estado de un botón de hombro (LB o RB)"""
    if activo:
        if boton not in (botones_izquierda if boton == vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER else botones_derecha):
            gamepad.press_button(boton)
            gamepad.update()
            if boton == vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER:
                botones_izquierda.add(boton)
            else:
                botones_derecha.add(boton)
    else:
        if boton in (botones_izquierda if boton == vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER else botones_derecha):
            gamepad.release_button(boton)
            gamepad.update()
            if boton == vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER:
                botones_izquierda.remove(boton)
            else:
                botones_derecha.remove(boton)

def actualizar_gatillo(trigger_type, activo):
    """Actualiza el estado de un gatillo (RT o LT)"""
    valor = config['GAMEPAD']['trigger_value'] if activo else 0
    if trigger_type == 'right_trigger':
        gamepad.right_trigger(value=valor)
    elif trigger_type == 'left_trigger':
        gamepad.left_trigger(value=valor)
    gamepad.update()

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

print("Iniciando simulación de gamepad con soporte para dos manos...")
print("Mano izquierda: D-Pad, LB, LT")
print("Mano derecha: A/B/X/Y, RB, RT")
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
                
                # Extraer coordenadas
                coords = np.array([[lm.x, lm.y] for lm in hand_landmarks.landmark])
                
                # Normalizar respecto a muñeca si está configurado
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

        # Actualizar gamepad según gestos detectados por cada mano
        # MANO IZQUIERDA: D-Pad, LB, LT
        if gestures_detected['Left'] is not None:
            gesture = gestures_detected['Left']
            
            # D-Pad
            dpad_button = gesture_to_dpad.get(gesture, 0)
            actualizar_dpad(dpad_button)
            
            # LB (Left Bumper)
            lb_button = gesture_to_shoulder_buttons.get(gesture)
            if lb_button == vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER:
                actualizar_boton_hombro(lb_button, True)
            else:
                actualizar_boton_hombro(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER, False)
            
            # LT (Left Trigger)
            lt_active = gesture_to_triggers.get(gesture) == 'left_trigger'
            actualizar_gatillo('left_trigger', lt_active)
        else:
            # Liberar todos los controles de la mano izquierda
            actualizar_dpad(0)
            actualizar_boton_hombro(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER, False)
            actualizar_gatillo('left_trigger', False)

        # MANO DERECHA: A/B/X/Y, RB, RT
        if gestures_detected['Right'] is not None:
            gesture = gestures_detected['Right']
            
            # Botones de acción A/B/X/Y
            action_button = gesture_to_action_buttons.get(gesture, 0)
            actualizar_botones_accion(action_button)
            
            # RB (Right Bumper)
            rb_button = gesture_to_shoulder_buttons.get(gesture)
            if rb_button == vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER:
                actualizar_boton_hombro(rb_button, True)
            else:
                actualizar_boton_hombro(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER, False)
            
            # RT (Right Trigger)
            rt_active = gesture_to_triggers.get(gesture) == 'right_trigger'
            actualizar_gatillo('right_trigger', rt_active)
        else:
            # Liberar todos los controles de la mano derecha
            actualizar_botones_accion(0)
            actualizar_boton_hombro(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER, False)
            actualizar_gatillo('right_trigger', False)

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
    # Liberar todos los botones al cerrar
    actualizar_dpad(0)
    actualizar_botones_accion(0)
    actualizar_boton_hombro(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER, False)
    actualizar_boton_hombro(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER, False)
    actualizar_gatillo('left_trigger', False)
    actualizar_gatillo('right_trigger', False)
    
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("Simulación finalizada")
