import serial
import json
import time
import platform
import sys

import paho.mqtt.client as mqtt

class ArduinoBridge:
    """
    Bridge Arduino → MQTT - Version compatible avec toutes les versions
    Fonctionne avec paho-mqtt 1.6.1, 2.0.0, 2.1.0, etc.
    """
    
    def __init__(self, baudrate=115200, broker="localhost", port=1883):
        self.baudrate = baudrate
        self.broker = broker
        self.mqtt_port = port
        self.ser = None
        self.running = False
        self.client = None
        self.connected_mqtt = False
        self.last_read_time = time.time()
        self.watchdog_timeout = 5
        
        self._init_mqtt()
        
    def _init_mqtt(self):
        """Initialiser MQTT - Compatible avec toutes les versions"""
        try:
            # Cette syntaxe fonctionne avec paho-mqtt 1.x et 2.x
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.connect(self.broker, self.mqtt_port, 60)
            self.client.loop_start()
            print("✅ [MQTT] Client initialisé")
        except Exception as e:
            print(f"❌ [MQTT] Erreur initialisation : {e}")
            sys.exit(1)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de connexion MQTT"""
        if rc == 0:
            self.connected_mqtt = True
            print("✅ [MQTT] Connecté au broker (localhost:1883)")
        else:
            print(f"❌ [MQTT] Erreur connexion (code {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback de déconnexion MQTT"""
        self.connected_mqtt = False
        if rc != 0:
            print(f"⚠️  [MQTT] Déconnecté (code {rc})")
    
    def detect_arduino_port(self):
        """
        Auto-détecte le port Arduino sur Windows (COM1-COM9)
        """
        print(f"🔍 [SERIAL] Détection du port Arduino (Windows)...")
        
        # Windows: COM1-COM9
        for port_num in range(1, 10):
            port_name = f"COM{port_num}"
            try:
                ser = serial.Serial(port_name, self.baudrate, timeout=1)
                # Attendre le reset Arduino
                time.sleep(0.5)
                ser.reset_input_buffer()
                
                print(f"✅ [SERIAL] Arduino trouvé sur {port_name}")
                return ser
            except (serial.SerialException, OSError):
                continue
        
        print(f"❌ [SERIAL] Arduino non détecté sur COM1-COM9")
        return None
    
    def start(self):
        """Démarrer la boucle de lecture et publication"""
        self.running = True
        
        # Chercher l'Arduino
        self.ser = self.detect_arduino_port()
        if not self.ser:
            print("❌ [BRIDGE] Impossible de continuer sans Arduino")
            print("💡 Vérifier:")
            print("   1. Arduino est connecté en USB")
            print("   2. Gestionnaire des périphériques → Ports (COM et LPT)")
            print("   3. Arduino est sur COM3, COM4, etc.")
            sys.exit(1)
        
        print("\n🚀 [BRIDGE] Démarrage de la boucle de publication MQTT...\n")
        
        try:
            while self.running:
                data = self._read_serial()
                
                if data:
                    self.last_read_time = time.time()
                    self._publish_mqtt(data)
                else:
                    # Vérifier le watchdog
                    elapsed = time.time() - self.last_read_time
                    if elapsed > self.watchdog_timeout:
                        print(f"⚠️  [WATCHDOG] Arduino ne répond plus ({elapsed:.1f}s)")
                        # Tenter une reconnexion
                        self._reconnect_serial()
                
                time.sleep(0.05)  # 50ms entre les lectures
        
        except KeyboardInterrupt:
            print("\n\n🛑 [BRIDGE] Arrêt du service...")
            self.stop()
    
    def _read_serial(self):
        """Lire une ligne JSON depuis l'Arduino"""
        try:
            if self.ser and self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                
                if line:
                    # Valider que c'est du JSON
                    data = json.loads(line)
                    return data
        
        except json.JSONDecodeError as e:
            print(f"⚠️  [SERIAL] JSON invalide : {e}")
        except UnicodeDecodeError as e:
            print(f"⚠️  [SERIAL] Erreur décodage : {e}")
        except Exception as e:
            print(f"❌ [SERIAL] Erreur lecture : {e}")
        
        return None
    
    def _publish_mqtt(self, data):
        """Publier les données sur MQTT"""
        if not self.connected_mqtt:
            print("⚠️  [MQTT] Non connecté, tentative de reconnexion...")
            return
        
        try:
            # Publier les données brutes
            payload = json.dumps(data)
            self.client.publish(
                "shos/sensors/raw",
                payload,
                qos=1,  # Au moins une fois
                retain=False
            )
            
            print(f"📤 [MQTT] Publiée : {payload}")
        
        except Exception as e:
            print(f"❌ [MQTT] Erreur sérialisation : {e}")
    
    def _reconnect_serial(self):
        """Tenter une reconnexion au port série"""
        print("🔄 [SERIAL] Tentative de reconnexion...")
        
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
        
        time.sleep(1)
        self.ser = self.detect_arduino_port()
        
        if self.ser:
            self.last_read_time = time.time()
            print("✅ [SERIAL] Reconnecté")
        else:
            print("❌ [SERIAL] Reconnexion échouée")
    
    def stop(self):
        """Arrêter le bridge proprement"""
        self.running = False
        
        if self.ser:
            self.ser.close()
            print("✅ [SERIAL] Port fermé")
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("✅ [MQTT] Déconnecté")
        
        print("✅ [BRIDGE] Service arrêté")


def main():
    """Point d'entrée du Bridge"""
    print("""
    ╔═══════════════════════════════════════╗
    ║   S.H.O.S ARDUINO BRIDGE V2.0         ║
    ║   Serial → MQTT Bridge                ║
    ║   Windows Compatible Edition          ║
    ║   (Compatible paho-mqtt 1.x et 2.x)   ║
    ╚═══════════════════════════════════════╝
    """)
    
    bridge = ArduinoBridge(
        baudrate=115200,
        broker="localhost",
        port=1883
    )
    
    bridge.start()


if __name__ == "__main__":
    main()
