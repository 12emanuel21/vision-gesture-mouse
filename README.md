# Vision Gesture Controller & Virtual Mouse

> Controlador de interfaz gráfica (Touchless HCI) en tiempo real mediante visión artificial. Integra seguimiento articular con MediaPipe Hands, filtrado cinemático EMA, emulación de periféricos y navegación por gestos en primer plano flotante (HUD).

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=flat&logo=opencv&logoColor=white)](https://opencv.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Landmark%20Tracking-0097A7?style=flat)](https://developers.google.com/mediapipe)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Visión General & Objetivo

Este sistema transforma cualquier cámara RGB estándar en un dispositivo de control de entrada para el sistema operativo sin requerir hardware dedicado. A diferencia de soluciones básicas de seguimiento, implementa:
* **HUD Flotante TopMost:** Ventana de telemetría visual compacta (PiP) configurada para permanecer siempre visible sobre el entorno de escritorio mientras se navega o trabaja.
* **Máquina de Estados Gestuales:** Detección diferenciada de puntero, clics, scroll continuo y cambio de pestañas de navegador/editor mediante combinaciones de pinza (*pinch gestures*).
* **Filtrado Exponencial (EMA):** Atenuación algorítmica del temblor manual sin latencia perceptible.

---

## ⚙️ Decisiones de Ingeniería & Algoritmos

* **Suavizado Cinemático por EMA (Exponential Moving Average):**  
  Para eliminar el temblor natural de la mano sin comprometer la respuesta táctil, el puntero utiliza un filtro exponencial:
  $$\text{current}_{x,y} = \text{prev}_{x,y} + \frac{\text{target}_{x,y} - \text{prev}_{x,y}}{\text{SMOOTHING}}$$
* **Medición de Distancias Euclidianas 2D:**  
  Los gestos de pinza se calculan directamente en píxeles del frame capturado:
  $$d = \sqrt{(x_1 - x_2)^2 + (y_1 - y_2)^2}$$
  Esto desacopla la sensibilidad del clic de la resolución de la pantalla de salida y evita disparos accidentales en diferentes relaciones de aspecto.
* **Navegación de Pestañas (Pinch Navigation):**  
  Implementación de estados de transición independientes con temporizadores (`TAB_CHANGE_COOLDOWN = 1.0s` y `CLICK_COOLDOWN = 0.5s`) para desacoplar el movimiento del cursor de los disparadores por atajo de teclado (`Ctrl+Tab`, `Ctrl+Shift+Tab`).
* **Scroll Proporcional No Bloqueante:**  
  Detección de postura paralela entre dedo índice y medio. El cálculo diferencial de $\Delta Y$ alimenta dinámicamente la rueda de desplazamiento (`pyautogui.scroll`) en función de la aceleración del usuario.

---

## 🖐️ Mapeo de Gestos y Atajos

| Gesto / Postura Articular | Acción del Sistema | Mecanismo de Disparo |
| :--- | :--- | :--- |
| **Índice extendido** | Movimiento de cursor | Interpolación EMA sobre `Landmark 8` |
| **Pinza: Pulgar + Índice** | Clic Izquierdo | Distancia euclidiana $< 30\text{ px}$ |
| **Pinza: Pulgar + Medio** | Clic Derecho | Distancia euclidiana $< 30\text{ px}$ |
| **Pinza: Pulgar + Anular** | Pestaña Anterior (`Ctrl+Shift+Tab`) | Distancia euclidiana $< 30\text{ px}$ con cooldown 1s |
| **Pinza: Pulgar + Meñique** | Pestaña Siguiente (`Ctrl+Tab`) | Distancia euclidiana $< 30\text{ px}$ con cooldown 1s |
| **Índice + Medio erguidos paralelos** | Scroll Vertical Dinámico | Distancia entre puntas $< 35\text{ px}$ |

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
* Python 3.10 o superior (ejecución nativa en Windows recomendada para acceso completo a APIs de emulación de eventos).
* Cámara web funcional (índice 0).

### 1. Clonar e Instalar Dependencias
```bash
git clone [https://github.com/12emanuel21/vision-gesture-mouse.git](https://github.com/12emanuel21/vision-gesture-mouse.git)
cd vision-gesture-mouse

python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
