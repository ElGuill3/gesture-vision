"""
Utilidad para listar todas las cámaras disponibles en el sistema
Útil para encontrar el índice de NVIDIA Broadcast u otras cámaras virtuales
"""


def main():
    import cv2

    print("=" * 60)
    print("LISTADO DE CÁMARAS DISPONIBLES")
    print("=" * 60)

    available_cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                available_cameras.append({
                    'index': i,
                    'width': width,
                    'height': height
                })
                print(f"Cámara {i}: Disponible ({width}x{height})")
            cap.release()
        else:
            print(f"Cámara {i}: No disponible")

    print("=" * 60)
    if available_cameras:
        print(f"\nTotal de cámaras disponibles: {len(available_cameras)}")
        print("\nPara usar una cámara específica, edita config/config.yaml:")
        print("  CAMERA:")
        print(f"    camera_index: {available_cameras[0]['index']}  # Cambia este número")
    else:
        print("\nNo se encontraron cámaras disponibles")


if __name__ == "__main__":
    main()
