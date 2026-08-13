import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

#Obtener los estilos por defecto de los Landmarks y las conexiones
landmarks_style = mp_drawing_styles.get_default_hand_landmarks_style()
connections_style = mp_drawing_styles.get_default_hand_connections_style()

#Configurar los colores para los Landmarks y las Conexiones
color1 = (0, 0, 255)
color2 = (0, 0, 255)

#Recorrer el diccionario de los Landmarks para reemplazar el color
for color in landmarks_style:
    landmarks_style[color] = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)

#Recorrer el diccionario de las conexiones para reemplazar el color    
for color in connections_style:
    connections_style[color] = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)

#Configurar la captura de video de la Webcam
cap = cv2.VideoCapture(0)
with mp_hands.Hands(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.75,
    max_num_hands=2) as hands:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Empty frame")
                break
            
            #Voltear la imagen horizontalmente para obtener la vista correcta
            image = cv2.flip(image, 1)
            
            image.flags.writeable = False
            h, w, _ = image.shape            
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(image)
            
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    
                    #Obtener las coordenadas X e Y de los Landmarks
                    x_list = [int(lm.x * w) for lm in hand_landmarks.landmark]
                    y_list = [int(lm.y * h) for lm in hand_landmarks.landmark]
                    
                    #Calcular el BoundingBox
                    x_min, x_max = min(x_list) - 25, max(x_list) + 25
                    y_min, y_max = min(y_list) - 25, max(y_list) + 25
                    
                    #Dibujar el rectangulo de la mano en el cuadro de video invertido
                    cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
                    
                    #Imprimir los Landmarks
                    print("HAND_LANDMARKS:", hand_landmarks )
                    
                    #Mostrar los Landmarks y las conexiones de la mano
                    mp_drawing.draw_landmarks(
                        image,
                        landmark_list=hand_landmarks,
                        connections=mp_hands.HAND_CONNECTIONS,
                        landmark_drawing_spec=landmarks_style,
                        connection_drawing_spec=connections_style)
                    
                    #Obtener el label izquierda/derecha
                    label = handedness.classification[0].label
                    
                    #Mostrar el Label en Español
                    label_to_show = "Izquierda" if label == "Left" else "Derecha"
                    
                    #Dibujar label sobre el cuadro de la imagen de de forma invertida
                    cv2.putText(image, label_to_show, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    
            #Se voltea la imagen horizontalmente
            cv2.imshow('MediaPipe Hands', image)
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
cap.release()