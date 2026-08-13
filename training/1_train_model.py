"""
Script 1: Entrenamiento del Modelo de Red Neuronal
Entrena un modelo de clasificación de gestos usando TensorFlow/Keras
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import tensorflow as tf
from tensorflow import keras
import joblib
import matplotlib.pyplot as plt
import yaml
import os
import sys

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar configuración
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("=" * 60)
print("ENTRENAMIENTO DEL MODELO DE GESTOS")
print("=" * 60)

# --- Configuración de GPU ---
if config['TRAINING']['use_gpu']:
    print("\nGPUs disponibles:", tf.config.list_physical_devices('GPU'))
    
    if config['TRAINING']['gpu_memory_growth']:
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                print(f"Configuradas {len(gpus)} GPU(s) con crecimiento dinámico de memoria")
            except RuntimeError as e:
                print(f"Error configurando GPU: {e}")
        else:
            print("No se encontraron GPUs, usando CPU")
    else:
        print("Usando GPU sin crecimiento dinámico de memoria")
else:
    print("GPU deshabilitada en configuración, usando CPU")

# --- Paso 1: Cargar y preprocesar los datos ---
print("\n[1/6] Cargando dataset...")
dataset_path = config['PREPROCESSING']['output_csv']
if not os.path.exists(dataset_path):
    raise FileNotFoundError(f"No se encontró el dataset en: {dataset_path}")

df = pd.read_csv(dataset_path)
X = df.drop('label', axis=1).values
y = df['label'].values

print(f"  - Total de muestras: {len(X)}")
print(f"  - Número de características: {X.shape[1]}")
print(f"  - Número de clases: {len(np.unique(y))}")

# Codificar etiquetas a enteros
print("\n[2/6] Codificando etiquetas...")
le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"  - Clases: {list(le.classes_)}")

# Dividir datos en entrenamiento y testeo
print("\n[3/6] Dividiendo dataset...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, 
    test_size=config['TRAINING']['validation_split'], 
    random_state=config['TRAINING']['random_state'], 
    stratify=y_encoded
)
print(f"  - Entrenamiento: {len(X_train)} muestras")
print(f"  - Validación: {len(X_test)} muestras")

# Escalar los datos
print("\n[4/6] Escalando características...")
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Asegurar tipo de dato correcto
X_train = X_train.astype(np.float32)
X_test = X_test.astype(np.float32)

# --- Paso 2: Definir la arquitectura del modelo ---
print("\n[5/6] Construyendo modelo...")
model_config = config['TRAINING']['model_architecture']
layers = model_config['layers']
dropout_rates = model_config['dropout_rates']
activation = model_config['activation']

model = keras.Sequential()
model.add(keras.layers.Input(shape=(X_train.shape[1],)))

for i, (neurons, dropout) in enumerate(zip(layers, dropout_rates)):
    model.add(keras.layers.Dense(neurons, activation=activation))
    model.add(keras.layers.Dropout(dropout))

# Capa de salida
model.add(keras.layers.Dense(len(le.classes_), activation='softmax'))

print(f"  - Arquitectura: {[X_train.shape[1]] + layers + [len(le.classes_)]}")

# --- Paso 3: Compilar el modelo ---
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=config['TRAINING']['learning_rate']),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Resumen del modelo
print("\nResumen del modelo:")
model.summary()

# --- Función para graficar el historial de entrenamiento ---
def plot_training_history(history):
    """Grafica el historial de entrenamiento"""
    os.makedirs(os.path.dirname(config['TRAINING']['history_plot']), exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Gráfica de pérdida
    ax1.plot(history.history['loss'], label='Pérdida de Entrenamiento', color='blue')
    ax1.plot(history.history['val_loss'], label='Pérdida de Validación', color='red')
    ax1.set_title('Pérdida del Modelo')
    ax1.set_xlabel('Época')
    ax1.set_ylabel('Pérdida')
    ax1.legend()
    ax1.grid(True)
    
    # Gráfica de precisión
    ax2.plot(history.history['accuracy'], label='Precisión de Entrenamiento', color='blue')
    ax2.plot(history.history['val_accuracy'], label='Precisión de Validación', color='red')
    ax2.set_title('Precisión del Modelo')
    ax2.set_xlabel('Época')
    ax2.set_ylabel('Precisión')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(config['TRAINING']['history_plot'], dpi=300, bbox_inches='tight')
    print(f"\nGráfica guardada en: {config['TRAINING']['history_plot']}")
    plt.close()

# --- Paso 4: Entrenar el modelo ---
print("\n[6/6] Entrenando modelo...")
print(f"  - Épocas: {config['TRAINING']['epochs']}")
print(f"  - Batch size: {config['TRAINING']['batch_size']}")
print(f"  - Learning rate: {config['TRAINING']['learning_rate']}")
print("\nIniciando entrenamiento...")

history = model.fit(
    X_train, y_train,
    epochs=config['TRAINING']['epochs'],
    batch_size=config['TRAINING']['batch_size'],
    validation_data=(X_test, y_test),
    verbose=1
)

# --- Paso 5: Graficar el historial de entrenamiento ---
print("\nGenerando gráficas de entrenamiento...")
plot_training_history(history)

# --- Paso 6: Guardar el modelo entrenado y utilidades ---
print("\nGuardando modelo y utilidades...")
os.makedirs(os.path.dirname(config['TRAINING']['model_output']), exist_ok=True)
os.makedirs(os.path.dirname(config['TRAINING']['scaler_output']), exist_ok=True)
os.makedirs(os.path.dirname(config['TRAINING']['label_encoder_output']), exist_ok=True)

model.save(config['TRAINING']['model_output'])
joblib.dump(scaler, config['TRAINING']['scaler_output'])
joblib.dump(le, config['TRAINING']['label_encoder_output'])

print(f"  - Modelo guardado en: {config['TRAINING']['model_output']}")
print(f"  - Scaler guardado en: {config['TRAINING']['scaler_output']}")
print(f"  - Label encoder guardado en: {config['TRAINING']['label_encoder_output']}")

# Evaluación final
print("\n" + "=" * 60)
print("EVALUACIÓN FINAL")
print("=" * 60)
test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"Pérdida en test: {test_loss:.4f}")
print(f"Precisión en test: {test_accuracy:.4f}")
print("=" * 60)
print("\nEntrenamiento completado exitosamente!")


