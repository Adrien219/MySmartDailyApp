import eventlet
eventlet.monkey_patch()

import sys, os, time, json, logging, psutil, threading
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
from paho.mqtt import client as mqtt_client
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("S.H.O.S_FINAL")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shos-final-2026'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

mqtt_connected = False
last_sensor_data = {}
last_esp32_data = {}
last_mobile_data = {}
last_frame = None
connected_clients = 0

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
            if msg.topic == "shos/sensors/normalized":
                data = json.loads(msg.payload.decode('utf-8'))
                last_sensor_data = data
                socketio.emit('sensor_update', data)
            
            elif msg.topic == "shos/sensors/esp32":
                data = json.loads(msg.payload.decode('utf-8'))
                last_esp32_data = data
                socketio.emit('esp32_update', data)
            
            elif msg.topic == "shos/sensors/mobile":
                data = json.loads(msg.payload.decode('utf-8'))
                last_mobile_data = data
                socketio.emit('mobile_update', data)
            
            elif "alert" in msg.topic:
                alert = json.loads(msg.payload.decode('utf-8'))
                if "critical" in msg.topic:
                    socketio.emit('alert_critical', alert)
                else:
                    socketio.emit('alert_warning', alert)
        except Exception as e:
            logger.error(f"❌ Erreur MQTT: {e}")

mqtt_handler = MQTTHandler()

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/profiles')
def profiles():
    return render_template('profiles.html')

@app.route('/diagnostic')
def diagnostic():
    return render_template('diagnostic.html')

@app.route('/mobile')
def mobile():
    return render_template('mobile.html')

@app.route('/esp32_cam')
def esp32_cam():
    return render_template('esp32_cam.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/profiles')
def api_profiles():
    profiles_file = Path(__file__).parent / 'data' / 'profiles.json'
    if profiles_file.exists():
        with open(profiles_file) as f:
            return jsonify(json.load(f))
    return jsonify({})

@app.route('/api/sensors/latest')
def api_sensors():
    return jsonify({
        'arduino': last_sensor_data,
        'esp32': last_esp32_data,
        'mobile': last_mobile_data
    })

@app.route('/api/system/status')
def api_status():
    return jsonify({
        'mqtt': mqtt_handler.connected,
        'clients': connected_clients,
        'timestamp': time.time()
    })

@app.route('/video_feed')
def video_feed():
    def gen_frames():
        global last_frame
        while True:
            if last_frame:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n' 
                       b'Content-Length: ' + str(len(last_frame)).encode() + b'\r\n\r\n' 
                       + last_frame + b'\r\n')
            eventlet.sleep(0.04)
    
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ============================================================================
# SOCKET.IO EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients += 1
    logger.info(f"✅ Client connecté (Total: {connected_clients})")
    socketio.start_background_task(background_monitor)
    emit('connection_response', {'data': 'Connecté à S.H.O.S V3'})

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients
    connected_clients = max(0, connected_clients - 1)

@socketio.on('request_data')
def handle_request_data():
    emit('sensor_data_response', {
        'sensors': last_sensor_data,
        'esp32': last_esp32_data,
        'mobile': last_mobile_data
    })

@socketio.on('request_status')
def handle_request_status():
    emit('mqtt_status', {'connected': mqtt_handler.connected})

@socketio.on('ping')
def handle_ping():
    emit('pong')

# ============================================================================
# MONITORING
# ============================================================================

def background_monitor():
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            temp = 0
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = round(int(f.read()) / 1000, 1)
            except:
                temp = 0
            
            socketio.emit('sys_update', {
                'cpu': round(cpu, 1),
                'ram': round(ram, 1),
                'disk': round(disk, 1),
                'temp': temp
            })
            
            socketio.sleep(2)
        except Exception as e:
            logger.error(f"❌ Erreur monitoring: {e}")
            socketio.sleep(2)

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    logger.info("""
    ╔════════════════════════════════════╗
    ║   S.H.O.S V3.0 FINAL - COMPLET    ║
    ║                                    ║
    ║  • Dashboard temps réel            ║
    ║  • Gestion profils drag-drop       ║
    ║  • Diagnostic 10 sections          ║
    ║  • Capteurs téléphone              ║
    ║  • Streaming ESP32                 ║
    ║  • Reconnaissance faciale          ║
    ║                                    ║
    ╚════════════════════════════════════╝
    """)
    
    logger.info("🌐 Interface: http://localhost:5000")
    logger.info("Lancer avec: python3 app_final_complete.py")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
