# GestureVision

Sistema de detección y clasificación de gestos de manos en tiempo real usando MediaPipe Hands y redes neuronales, con una integración opcional para mapearlos a un gamepad virtual Xbox 360.

## 📋 Descripción

Este proyecto permite detectar y clasificar gestos de manos capturados por una cámara web. Utiliza:
- **MediaPipe Hands** para la detección de landmarks de la mano
- **Red Neuronal (TensorFlow/Keras)** para la clasificación de gestos
- **vgamepad** para la integración opcional con un gamepad Xbox 360

## 🏗️ Estructura del Proyecto

```
gesture-vision/
├── config/
│   └── config.yaml              # Configuración principal del sistema
├── preprocessing/
│   └── 0_create_dataset.py      # Script para crear el dataset de gestos
├── training/
│   └── 1_train_model.py         # Script para entrenar el modelo
├── inference/
│   └── 2_real_time_inference.py # Script de inferencia en tiempo real
├── integrations/
│   └── gamepad/
│       ├── gamepad_simulation.py # Integración opcional con gamepad
│       └── requirements.txt      # Dependencia opcional de vgamepad
├── data/
│   ├── datasets/                 # Datasets CSV
│   └── models/                   # Modelos entrenados, scalers, encoders
├── results/
│   └── training/                 # Resultados de entrenamiento (gráficas)
├── utils/                        # Utilidades compartidas (futuro)
├── requirements.txt              # Dependencias del proyecto
└── README.md                     # Este archivo
```

## 🚀 Instalación

### Requisitos Previos

- Python 3.8 o superior
- Cámara web
- Windows 10/11 (solo para la integración opcional con vgamepad)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**

2. **Crear un entorno virtual (recomendado)**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

Para usar la integración opcional con gamepad:
```bash
pip install -r integrations/gamepad/requirements.txt
```

4. **Configurar el archivo de configuración**
   - Edita `config/config.yaml` según tus necesidades
   - Ajusta el índice de cámara si usas NVIDIA Broadcast u otra cámara virtual

## 📖 Uso

### Flujo de Trabajo Completo

#### 1. Crear Dataset de Gestos

Ejecuta el script de preprocesamiento para capturar gestos:

```bash
python preprocessing/0_create_dataset.py
```

**Instrucciones:**
- Presiona las teclas correspondientes mientras haces el gesto
- Las teclas están mapeadas en `config/config.yaml` bajo `GESTURE_CAPTURE`
- Presiona ESC para finalizar la captura
- El dataset se guardará en `data/datasets/dataset_gestos.csv`

**Teclas por defecto:**
- **D-Pad**: W (arriba), S (abajo), A (izquierda), D (derecha)
- **Diagonales**: Q (arriba-izquierda), E (arriba-derecha), Z (abajo-izquierda), X (abajo-derecha)
- **Botones**: F (X), G (A), H (Y), J (B), K (LB), L (LT), N (RB), M (RT)
- **Neutro**: O (opcional - ver nota abajo)

**Nota sobre el gesto "neutro":**
El gesto "neutro" es **opcional**. El sistema automáticamente no presiona ningún botón cuando:
- No se detecta ninguna mano
- La confianza de la predicción es menor al umbral configurado (`prediction_threshold` en `config.yaml`)

Solo necesitas entrenar un gesto "neutro" si quieres que el modelo aprenda explícitamente a reconocer "mano presente pero sin gesto específico". Para la mayoría de casos, no es necesario.

#### 2. Entrenar el Modelo

Una vez que tengas suficientes muestras (recomendado: 100+ por gesto), entrena el modelo:

```bash
python training/1_train_model.py
```

**Configuración:**
- Edita `config/config.yaml` bajo `TRAINING` para ajustar hiperparámetros
- El modelo se guardará en `data/models/modelo_gestos.h5`
- Se generarán gráficas de entrenamiento en `results/training/`

#### 3. Inferencia en Tiempo Real (Solo Visualización)

Para probar la detección sin gamepad:

```bash
python inference/2_real_time_inference.py
```

#### 4. Simulación de Gamepad

Para usar el gamepad virtual:

```bash
python integrations/gamepad/gamepad_simulation.py
```

**Nota:** Requiere permisos de administrador en Windows para crear el gamepad virtual.

## ⚙️ Configuración

### Archivo de Configuración (`config/config.yaml`)

El archivo YAML contiene todas las configuraciones del sistema:

#### MediaPipe
- `max_num_hands`: Número máximo de manos a detectar
- `min_detection_confidence`: Confianza mínima para detección
- `min_tracking_confidence`: Confianza mínima para tracking
- `model_complexity`: Complejidad del modelo (0, 1, 2)

#### Cámara
- `camera_index`: Índice de la cámara (0=por defecto, 1=NVIDIA Broadcast, etc.)
- `flip_horizontal`: Voltear imagen horizontalmente

#### Entrenamiento
- `epochs`: Número de épocas
- `batch_size`: Tamaño de batch
- `learning_rate`: Tasa de aprendizaje
- `layers`: Arquitectura de la red neuronal

#### Gamepad
- `gesture_to_dpad`: Mapeo de gestos a botones D-Pad
- `gesture_to_buttons`: Mapeo de gestos a botones A/B/X/Y/RB/LB
- `gesture_to_triggers`: Mapeo de gestos a gatillos RT/LT

## 🎮 Gestos Soportados

### D-Pad (Direcciones)
- `up`, `down`, `left`, `right`
- `upleft`, `upright`, `downleft`, `downright` (diagonales)

### Estado Neutro
- **Automático**: El sistema no presiona ningún botón cuando no hay mano detectada o la confianza es baja
- **Opcional**: Puedes entrenar un gesto `neutro` explícito si lo deseas (ver configuración)

### Botones
- `A`, `B`, `X`, `Y`
- `LB` (Left Bumper), `RB` (Right Bumper)

### Gatillos
- `RT` (Right Trigger), `LT` (Left Trigger)

## 🔧 Resolución de Problemas

### Error: "No se encontró el dataset"
- Asegúrate de ejecutar primero `preprocessing/0_create_dataset.py`
- Verifica que el archivo existe en `data/datasets/dataset_gestos.csv`

### Error: "No se encontraron los archivos del modelo"
- Ejecuta primero `training/1_train_model.py`
- Verifica que los archivos existen en `data/models/`

### Error al usar vgamepad
- Ejecuta el script como administrador
- Verifica que vgamepad esté instalado correctamente: `pip install vgamepad`

### Cámara no detecta
- Verifica el índice de cámara en `config/config.yaml`
- Para NVIDIA Broadcast, usa `camera_index: 1` o prueba otros índices
- Lista cámaras disponibles ejecutando:
```python
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Cámara {i}: Disponible")
        cap.release()
```

### Baja precisión del modelo
- Aumenta el número de muestras por gesto (recomendado: 200+)
- Ajusta hiperparámetros en `config/config.yaml`
- Aumenta el número de épocas de entrenamiento
- Verifica que los gestos sean consistentes durante la captura

## 📊 Mejores Prácticas

### Captura de Dataset
- Captura múltiples muestras de cada gesto (100-200 mínimo)
- Varía ligeramente la posición y orientación de la mano
- Asegúrate de tener buena iluminación
- Mantén la mano visible y completa en el frame

### Entrenamiento
- Divide el dataset en entrenamiento/validación (configurado automáticamente)
- Monitorea las gráficas de pérdida y precisión
- Si hay sobreajuste, aumenta el dropout o reduce la complejidad del modelo

### Inferencia
- Usa buena iluminación para mejor detección
- Mantén la mano a una distancia cómoda de la cámara
- Activa el suavizado de predicciones en la configuración para reducir fluctuaciones

## 🛠️ Desarrollo Futuro

- [ ] Soporte para múltiples manos simultáneas
- [ ] Detección de gestos dinámicos (movimientos)
- [ ] Interfaz gráfica para configuración
- [ ] Exportación de modelos a formato optimizado
- [ ] Soporte para otros tipos de gamepads

## 📝 Notas

- El proyecto está basado en la estructura del proyecto [shazam-v2](https://github.com/Julio-Schez/shazam-v2.git)
- Requiere Windows para vgamepad (no compatible con Linux/Mac directamente)
- Para mejor rendimiento, usa GPU con TensorFlow

## 📁 Archivos Antiguos

Los siguientes archivos en la raíz del proyecto son versiones antiguas y pueden ser eliminados:
- `hand_create_csv.py` → Reemplazado por `preprocessing/0_create_dataset.py`
- `model_training.py` → Reemplazado por `training/1_train_model.py`
- `real_time_inference.py` → Reemplazado por `inference/2_real_time_inference.py`
- `gamepad_simulation.py` → Reemplazado por `integrations/gamepad/gamepad_simulation.py`
- `hand_detection.py` → Script de prueba, puede mantenerse o eliminarse
- `cam_verify.py`, `hitbox_emulation.py` → Scripts auxiliares, pueden mantenerse

## 🔍 Utilidades

### Listar Cámaras Disponibles

Para encontrar el índice de tu cámara (útil para NVIDIA Broadcast):

```bash
python utils/list_cameras.py
```

Esto mostrará todas las cámaras disponibles y sus índices.

## 📄 Licencia

Este proyecto está optimizado para uso educativo y personal.

---

**Última actualización:** Noviembre 2025

