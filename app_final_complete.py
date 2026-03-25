import eventlet
eventlet.monkey_patch()

import sys, os, time, json, logging, psutil, threading, cv2
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
from paho.mqtt import client as mqtt_client
from datetime import datetime
from pathlib import Path

# Tentative d'import du module de gestes
try:
    from modules.hand_gesture import HandController
except ImportError:
    class HandController:
        def get_gesture(self, frame): return "NONE", frame

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("S.H.O.S_FINAL")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shos-final-2026'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

mqtt_connected = False
last_sensor_data = {}
last_esp32_data = {}
last_mobile_data = {}
last_frame = None       # Pour l'ESP32-CAM
last_frame_pi = None    # Pour la Caméra Raspberry (Gestes)
current_gesture = "NONE"
connected_clients = 0

# Configuration des Snapshots
SNAPSHOT_FOLDER = Path(__name__).parent / 'data' / 'snapshots'
if not SNAPSHOT_FOLDER.exists(): SNAPSHOT_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================================================
# GESTURE ENGINE (PI CAMERA)
# ============================================================================

def gesture_recognition_task():
    """Analyse la caméra locale via GStreamer pour Raspberry Pi."""
    global last_frame_pi, current_gesture
    logger.info("🚀 Moteur de gestes S.H.O.S activé")
    
    detector = HandController()
    
    # Pipeline GStreamer spécifique pour libcamera sur Raspberry Pi
    pipeline = (
        "libcamerasrc ! video/x-raw, width=640, height=480, framerate=30/1 ! "
        "videoconvert ! appsink"
    )
    
    # On tente GStreamer, si échec on revient au mode classique (V4L2)
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        logger.warning("⚠️ GStreamer non dispo, bascule sur V4L2 (/dev/video0)")
        cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            eventlet.sleep(0.1)
            continue
            
        # Détection des gestes
        gesture, processed_frame = detector.get_gesture(frame)
        
        # Emission si le geste change
        if gesture != "NONE" and gesture != current_gesture:
            current_gesture = gesture
            logger.info(f"🖐️ Geste détecté : {gesture}")
            socketio.emit('gesture_event', {'gesture': gesture})
            
            # --- CORRECTION : Enregistrement photo sur Geste "Salut" (Moteur démarré) ---
            if gesture == "SYSTEM_START":
                save_snapshot(processed_frame)

            handle_gesture_logic(gesture)

        # Encodage pour le flux vidéo (Dashboard/Diagnostic)
        _, buffer = cv2.imencode('.jpg', processed_frame)
        last_frame_pi = buffer.tobytes()
        
        eventlet.sleep(0.01)

# ============================================================================
# PLUGINS (Actions)
# ============================================================================

def handle_gesture_logic(gesture):
    """Logique de déclenchement des plugins système."""
    if gesture == "TRIGGER_ANALYSE":
        logger.info("🧠 Plugin : Analyse Florence-2 demandée")
    elif gesture == "READ_TEXT":
        logger.info("📖 Plugin : Lecture OCR demandée")
    elif gesture == "SYSTEM_STOP":
        logger.info("🛑 Plugin : Arrêt d'urgence/Veille")

def save_snapshot(frame):
    """Plugin : Enregistre une photo avec un texte d'état."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"shos_greet_{timestamp}.jpg"
    filepath = SNAPSHOT_FOLDER / filename
    
    # Ajout du texte d'état sur l'image
    text = f"S.H.O.S GREETING - {timestamp}"
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
    
    # Enregistrement
    cv2.imwrite(str(filepath), frame)
    logger.info(f"📸 Photo enregistrée : {filename}")
    socketio.emit('alert_warning', {'data': f"📸 Salut capturé : {filename}"})

# ============================================================================
# MQTT CLIENT
# ============================================================================

class MQTTHandler:
    def __init__(self, host='localhost', port=1883):
        self.host = host
        self.port = port
        self.connected = False
        self.client = None
        self._init()
    
    def _init(self):
        try:
            try:
                self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, "SHOS_FINAL")
            except:
                self.client = mqtt_client.Client("SHOS_FINAL")
            
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            logger.info("✅ MQTT Client initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur MQTT: {e}")
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        global mqtt_connected
        if rc == 0:
            self.connected = True
            mqtt_connected = True
            logger.info("📡 Connecté au broker MQTT")
            client.subscribe([
                ("shos/sensors/normalized", 1),
                ("shos/sensors/esp32", 1),
                ("shos/sensors/mobile", 1),
                ("shos/alert/critical", 2),
                ("shos/alert/warning", 1),
            ])
        else:
            self.connected = False
            mqtt_connected = False
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        global mqtt_connected
        self.connected = False
        mqtt_connected = False
    
    def _on_message(self, client, userdata, msg):
        global last_sensor_data, last_esp32_data, last_mobile_data
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            if msg.topic == "shos/sensors/normalized":
                last_sensor_data = payload
                socketio.emit('sensor_update', payload)
            elif msg.topic == "shos/sensors/esp32":
                last_esp32_data = payload
                socketio.emit('esp32_update', payload)
            elif msg.topic == "shos/sensors/mobile":
                last_mobile_data = payload
                socketio.emit('mobile_update', payload)
            elif "alert" in msg.topic:
                socketio.emit('alert_critical' if "critical" in msg.topic else 'alert_warning', payload)
        except Exception as e:
            logger.error(f"❌ Erreur parsing MQTT: {e}")

mqtt_handler = MQTTHandler()

# ============================================================================
# ROUTES & VIDEO STREAMING
# ============================================================================

@app.route('/')
def home(): return render_template('index.html')

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/diagnostic')
def diagnostic(): return render_template('diagnostic.html')

def stream_generator(source_attr):
    """Générateur générique pour les flux vidéo."""
    while True:
        frame = globals().get(source_attr)
        if frame:
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        eventlet.sleep(0.04)

@app.route('/video_feed')
def video_feed():
    return Response(stream_generator('last_frame'), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_pi')
def video_feed_pi():
    return Response(stream_generator('last_frame_pi'), mimetype='multipart/x-mixed-replace; boundary=frame')

# ============================================================================
# SOCKET.IO EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients += 1
    logger.info(f"✅ Client connecté (Total: {connected_clients})")
    emit('connection_response', {'data': 'Connecté à S.H.O.S V3'})

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients
    connected_clients = max(0, connected_clients - 1)

# ============================================================================
# MONITORING SYSTEME
# ============================================================================

def background_monitor():
    while True:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            temp = 0
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = round(int(f.read()) / 1000, 1)
            except: pass
            socketio.emit('sys_update', {'cpu': cpu, 'ram': ram, 'temp': temp})
            socketio.sleep(2)
        except Exception as e:
            logger.error(f"❌ Erreur monitoring: {e}")
            socketio.sleep(2)

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    logger.info("🚀 S.H.O.S V3.0 FINAL - Démarrage du système")
    
    # Lancement des threads de fond
    socketio.start_background_task(background_monitor)
    socketio.start_background_task(gesture_recognition_task)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
