import cv2
import mediapipe as mp
import sys
import pyautogui
import math
import time

# Variables globales para la navegación de pestañas (Pinch Navigation)
last_tab_change_time = 0.0
TAB_CHANGE_COOLDOWN = 1.0

def calculate_distance_px(lm1, lm2, frame_w, frame_h):
    """Calcula la distancia euclidiana en píxeles de la cámara entre dos landmarks."""
    x1, y1 = lm1.x * frame_w, lm1.y * frame_h
    x2, y2 = lm2.x * frame_w, lm2.y * frame_h
    return math.hypot(x1 - x2, y1 - y2)

def main():
    # Desactivar el retardo por defecto de PyAutoGUI para mayor velocidad/fluidez
    pyautogui.PAUSE = 0
    
    # Obtener la resolución de la pantalla dinámicamente
    try:
        screen_width, screen_height = pyautogui.size()
        print(f"Resolución de pantalla detectada: {screen_width}x{screen_height}")
    except Exception as e:
        print(f"Error al obtener la resolución de pantalla con PyAutoGUI: {e}", file=sys.stderr)
        print("Asegúrese de tener un entorno gráfico activo (X11/WSLg/Windows GUI).", file=sys.stderr)
        return

    # Inicializar MediaPipe Hands
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    # Configurar Hands para detectar una sola mano
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    # Capturar video de la cámara por defecto (índice 0)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara por defecto (índice 0).", file=sys.stderr)
        print("Por favor, asegúrese de que la cámara esté conectada y no esté siendo usada por otra aplicación.", file=sys.stderr)
        return

    print("Cámara iniciada correctamente. Presione 'q' en la ventana de video para salir.")

    global last_tab_change_time

    # Configuración de la ventana flotante (HUD / Picture-in-Picture)
    window_name = 'Deteccion de Mano - MediaPipe'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 350, 250)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    # Parámetros de suavizado (EMA) y tracking del cursor
    SMOOTHING = 5.0
    prev_x, prev_y = 0.0, 0.0
    hand_active = False

    # Variables locales para feedback visual temporal de cambio de pestañas
    tab_feedback_text = ""
    tab_feedback_time = 0.0

    # Parámetros y estados para el sistema de clics
    CLICK_THRESHOLD = 30.0    # Umbral de distancia en píxeles para clics
    CLICK_COOLDOWN = 0.5     # Cooldown en segundos entre clics
    last_click_time = 0.0
    left_clicked = False
    right_clicked = False

    # Parámetros y estados para el modo Scroll
    SCROLL_DIST_THRESHOLD = 35.0  # Distancia máxima entre índice y medio para activar scroll
    SCROLL_SENSITIVITY = 1.2      # Sensibilidad del scroll (factor multiplicador)
    scroll_mode_active = False
    prev_scroll_y = None

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo leer el frame de la cámara. Saliendo...", file=sys.stderr)
                break

            # Invertir el eje X de la cámara (efecto espejo visual)
            frame = cv2.flip(frame, 1)
            frame_h, frame_w, _ = frame.shape

            # MediaPipe requiere imágenes en formato RGB, pero OpenCV las lee en BGR
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Procesar el frame y buscar manos
            results = hands.process(rgb_frame)

            current_mode = "CURSOR"

            # Dibujar los landmarks y conexiones si se detecta una mano
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Dibujar los landmarks y sus conexiones estándar de fondo
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(220, 220, 220), thickness=1, circle_radius=1),
                        mp_drawing.DrawingSpec(color=(180, 180, 180), thickness=1, circle_radius=1)
                    )

                    # Obtener los landmarks necesarios
                    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    
                    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
                    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
                    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
                    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
                    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
                    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]

                    # Determinar si los dedos están levantados (abiertos) o cerrados
                    # (En MediaPipe, el eje Y va hacia abajo, por lo que menor Y significa más arriba)
                    index_open = index_tip.y < index_pip.y
                    middle_open = middle_tip.y < middle_pip.y
                    ring_closed = ring_tip.y > ring_pip.y
                    pinky_closed = pinky_tip.y > pinky_pip.y

                    # Calcular la distancia entre el dedo índice y medio en píxeles de cámara
                    dist_index_middle = calculate_distance_px(index_tip, middle_tip, frame_w, frame_h)

                    # Verificar condición de Modo Scroll:
                    # Índice y Medio levantados y pegados, mientras Anular y Meñique están cerrados.
                    is_scroll_pose = index_open and middle_open and ring_closed and pinky_closed and (dist_index_middle < SCROLL_DIST_THRESHOLD)

                    # Imprimir en consola las coordenadas normalizadas del Landmark 8 (índice)
                    print(f"Punta del dedo índice (Landmark 8) -> X: {index_tip.x:.4f}, Y: {index_tip.y:.4f}, Z: {index_tip.z:.4f}")

                    if is_scroll_pose:
                        current_mode = "SCROLL"
                        
                        # Feedback visual para modo Scroll: línea amarilla/celeste gruesa conectando índice y medio
                        x_index, y_index = int(index_tip.x * frame_w), int(index_tip.y * frame_h)
                        x_middle, y_middle = int(middle_tip.x * frame_w), int(middle_tip.y * frame_h)
                        cv2.line(frame, (x_index, y_index), (x_middle, y_middle), (0, 255, 255), 4)
                        cv2.circle(frame, (x_index, y_index), 8, (0, 255, 255), cv2.FILLED)
                        cv2.circle(frame, (x_middle, y_middle), 8, (0, 255, 255), cv2.FILLED)

                        posicion_actual_y = index_tip.y * screen_height

                        if prev_scroll_y is None:
                            prev_scroll_y = posicion_actual_y
                            continue

                        delta_y = (posicion_actual_y - prev_scroll_y) * SCROLL_SENSITIVITY
                        try:
                            pyautogui.scroll(int(delta_y))
                        except Exception:
                            pass
                        prev_scroll_y = posicion_actual_y
                        
                        # Al estar en scroll, desactivamos el estado activo del cursor
                        hand_active = False
                    else:
                        # Modo normal: Apagar modo scroll y ejecutar cursor + clics
                        scroll_mode_active = False
                        prev_scroll_y = None

                        # 1. Movimiento del cursor con suavizado (EMA)
                        target_x = index_tip.x * screen_width
                        target_y = index_tip.y * screen_height

                        if not hand_active:
                            prev_x, prev_y = target_x, target_y
                            hand_active = True

                        # Suavizado Exponencial (EMA)
                        current_x = prev_x + (target_x - prev_x) / SMOOTHING
                        current_y = prev_y + (target_y - prev_y) / SMOOTHING

                        try:
                            pyautogui.moveTo(int(current_x), int(current_y))
                        except pyautogui.FailSafeException:
                            print("Advertencia: Se activó el FailSafe de PyAutoGUI (cursor en esquina).")
                        except Exception:
                            pass

                        # Actualizar variables previas
                        prev_x, prev_y = current_x, current_y

                        # Lógica de Pinch Navigation para cambiar de pestañas (Anular y Meñique)
                        dist_thumb_ring = calculate_distance_px(thumb_tip, ring_tip, frame_w, frame_h)
                        dist_thumb_pinky = calculate_distance_px(thumb_tip, pinky_tip, frame_w, frame_h)

                        current_time = time.time()
                        if current_time - last_tab_change_time > TAB_CHANGE_COOLDOWN:
                            if dist_thumb_ring < 30.0:
                                pyautogui.hotkey('ctrl', 'shift', 'tab')
                                print("--> PESTAÑA IZQ (Ctrl+Shift+Tab)")
                                last_tab_change_time = current_time
                                tab_feedback_text = "PESTAÑA IZQ"
                                tab_feedback_time = current_time
                            elif dist_thumb_pinky < 30.0:
                                pyautogui.hotkey('ctrl', 'tab')
                                print("--> PESTAÑA DER (Ctrl+Tab)")
                                last_tab_change_time = current_time
                                tab_feedback_text = "PESTAÑA DER"
                                tab_feedback_time = current_time

                        # 2. Lógica de clics usando distancias euclidianas en píxeles de cámara
                        dist_thumb_index = calculate_distance_px(thumb_tip, index_tip, frame_w, frame_h)
                        dist_thumb_middle = calculate_distance_px(thumb_tip, middle_tip, frame_w, frame_h)

                        current_time = time.time()

                        # Clic Izquierdo (Pulgar + Índice)
                        if dist_thumb_index < CLICK_THRESHOLD:
                            x_thumb = int(thumb_tip.x * frame_w)
                            y_thumb = int(thumb_tip.y * frame_h)
                            x_index = int(index_tip.x * frame_w)
                            y_index = int(index_tip.y * frame_h)
                            cv2.line(frame, (x_thumb, y_thumb), (x_index, y_index), (0, 0, 255), 3)
                            cv2.circle(frame, (x_index, y_index), 10, (0, 0, 255), cv2.FILLED)
                            
                            if not left_clicked and (current_time - last_click_time > CLICK_COOLDOWN):
                                pyautogui.click()
                                print("--> ¡CLIC IZQUIERDO EJECUTADO!")
                                left_clicked = True
                                last_click_time = current_time
                        else:
                            left_clicked = False

                        # Clic Derecho (Pulgar + Medio)
                        if dist_thumb_middle < CLICK_THRESHOLD:
                            x_thumb = int(thumb_tip.x * frame_w)
                            y_thumb = int(thumb_tip.y * frame_h)
                            x_middle = int(middle_tip.x * frame_w)
                            y_middle = int(middle_tip.y * frame_h)
                            cv2.line(frame, (x_thumb, y_thumb), (x_middle, y_middle), (255, 0, 0), 3)
                            cv2.circle(frame, (x_middle, y_middle), 10, (255, 0, 0), cv2.FILLED)
                            
                            if not right_clicked and (current_time - last_click_time > CLICK_COOLDOWN):
                                pyautogui.click(button='right')
                                print("--> ¡CLIC DERECHO EJECUTADO!")
                                right_clicked = True
                                last_click_time = current_time
                        else:
                            right_clicked = False

                        # Feedback visual para navegación de pestañas (Anular y Meñique)
                        if dist_thumb_ring < 30.0:
                            x_thumb = int(thumb_tip.x * frame_w)
                            y_thumb = int(thumb_tip.y * frame_h)
                            x_ring = int(ring_tip.x * frame_w)
                            y_ring = int(ring_tip.y * frame_h)
                            cv2.line(frame, (x_thumb, y_thumb), (x_ring, y_ring), (255, 0, 255), 3)
                            cv2.circle(frame, (x_ring, y_ring), 10, (255, 0, 255), cv2.FILLED)

                        if dist_thumb_pinky < 30.0:
                            x_thumb = int(thumb_tip.x * frame_w)
                            y_thumb = int(thumb_tip.y * frame_h)
                            x_pinky = int(pinky_tip.x * frame_w)
                            y_pinky = int(pinky_tip.y * frame_h)
                            cv2.line(frame, (x_thumb, y_thumb), (x_pinky, y_pinky), (0, 0, 255), 3)
                            cv2.circle(frame, (x_pinky, y_pinky), 10, (0, 0, 255), cv2.FILLED)

                        # Dibujar círculos adicionales en los dedos activos para feedback visual constante en modo cursor
                        cv2.circle(frame, (int(thumb_tip.x * frame_w), int(thumb_tip.y * frame_h)), 6, (0, 255, 255), cv2.FILLED)
                        cv2.circle(frame, (int(index_tip.x * frame_w), int(index_tip.y * frame_h)), 6, (0, 255, 0), cv2.FILLED)
                        cv2.circle(frame, (int(middle_tip.x * frame_w), int(middle_tip.y * frame_h)), 6, (255, 255, 0), cv2.FILLED)
                        cv2.circle(frame, (int(ring_tip.x * frame_w), int(ring_tip.y * frame_h)), 6, (255, 0, 255), cv2.FILLED)
                        cv2.circle(frame, (int(pinky_tip.x * frame_w), int(pinky_tip.y * frame_h)), 6, (0, 0, 255), cv2.FILLED)
            else:
                # Restablecer estados si no se detecta ninguna mano
                hand_active = False
                scroll_mode_active = False
                prev_scroll_y = None

            # Mostrar estado actual de cooldown y modo en la ventana
            if current_mode == "SCROLL":
                cv2.putText(frame, "MODO: SCROLL", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "MODO: CURSOR", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if time.time() - last_click_time < CLICK_COOLDOWN:
                    cv2.putText(frame, "ESTADO: COOLDOWN CLIC", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                else:
                    cv2.putText(frame, "ESTADO: LISTO CLIC", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Mostrar feedback de cambio de pestañas si ocurrió hace menos de 1 segundo
            if time.time() - tab_feedback_time < 1.0:
                cv2.putText(frame, tab_feedback_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            # Mostrar el frame con las detecciones y feedback visual en ventana flotante
            cv2.imshow(window_name, frame)

            # Salir del bucle si se presiona la tecla 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Cerrando la aplicación por petición del usuario.")
                break

    except Exception as e:
        print(f"Ocurrió un error inesperado durante la ejecución: {e}", file=sys.stderr)

    finally:
        # Liberar la cámara y cerrar las ventanas de OpenCV
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        print("Recursos liberados y ventanas cerradas limpiamente.")

if __name__ == "__main__":
    main()
