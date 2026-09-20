# Vision Gesture Controller & Virtual Mouse

> Controlador de interfaz gráfica (HCI) en tiempo real mediante visión por computador, detección de landmarks articulares con MediaPipe Hands y emulación cinemática del cursor y gestos con OpenCV y PyAutoGUI.

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=flat&logo=opencv&logoColor=white)](https://opencv.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Landmark%20Tracking-0097A7?style=flat)](https://developers.google.com/mediapipe)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Visión General & Objetivo

Este proyecto implementa un controlador sin contacto (touchless HCI) que mapea la cinemática de la mano capturada por una cámara estándar (RGB) hacia eventos del sistema operativo (Windows/Linux GUI). Diseñado para proporcionar control fluido del puntero del mouse, scroll bidireccional y disparadores de clics de baja latencia sin necesidad de sensores externos ni hardware especializado.

---

## ⚙️ Decisiones Técnicas y Matemáticas del Sistema

* **Pipeline de Tracking Articular:** Uso del grafo `MediaPipe Hands` configurado con detección monomanual (`max_num_hands=1`) y umbrales estrictos de confianza (`0.7` detección / `0.7` tracking) para minimizar falsos positivos y jittering.
* **Filtro de Suavizado Cinemático:** Atenuación exponencial para el desplazamiento del cursor mediante interpolación lineal ponderada (`current = prev + (target - prev) / factor`). Esto elimina el temblor natural de la mano sin penalizar la latencia perceptible.
* **Detección de Clics por Distancia Euclidiana:** Disparo de clic izquierdo y derecho evaluando la norma vectorial $\sqrt{(x_1 - x_2)^2 + (y_1 - y_2)^2}$ en el espacio 2D de la cámara entre el pulgar (`THUMB_TIP`) y las puntas del índice (`INDEX_FINGER_TIP`) o medio (`MIDDLE_FINGER_TIP`), operando bajo un cooldown temporal (`0.5s`) para evitar eventos fantasma o rebotes rápidos.
* **Máquina de Estados de Gestos (Modo Scroll):** Segmentación por postura articular: cuando el índice y medio permanecen erguidos y convergentes (`dist < 35px`) mientras anular y meñique están ocluidos, el sistema conmuta a modo `SCROLL`. La derivada temporal de la coordenada Y ($\Delta Y$) se proyecta directamente a la rueda de desplazamiento (`pyautogui.scroll`) con sensibilidad ajustable.
* **Inversión y Normalización de Cámara:** Compensación del efecto espejo (`cv2.flip`) y normalización espacial adaptativa contra la resolución física de la pantalla (`pyautogui.size()`).

---

## 🖐️ Mapeo de Gestos

| Gesto / Postura | Acción en Sistema Operativo | Condición Articular |
| :--- | :--- | :--- |
| **Puntero activo** | Mover cursor (Interpolado) | Dedo índice erguido (`Landmark 8`) |
| **Pinza Pulgar + Índice** | Clic Izquierdo (`click()`) | Distancia euclidiana $< 30\text{ px}$ |
| **Pinza Pulgar + Medio** | Clic Derecho (`right click`) | Distancia euclidiana $< 30\text{ px}$ |
| **Índice + Medio paralelos** | Scroll Vertical Dinámico | Ambos dedos erguidos, anular y meñique plegados |

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
* Python 3.10 o superior.
* Cámara web activa (puerto index 0 por defecto).
* Servidor gráfico activo (Windows nativo, WSL2 con WSLg, o Linux X11/Wayland).

### 1. Clonar y Configurar Entorno
```bash
git clone [https://github.com/12emanuel21/vision-gesture-mouse.git](https://github.com/12emanuel21/vision-gesture-mouse.git)
cd vision-gesture-mouse

python -m venv .venv
source .venv/bin/activate  # En Windows CMD/PowerShell: .venv\Scripts\activate
pip install -r requirements.txt