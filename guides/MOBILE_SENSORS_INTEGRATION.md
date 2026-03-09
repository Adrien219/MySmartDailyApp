# 📱 GUIDE D'INTÉGRATION - CAPTEURS TÉLÉPHONE

## Vue d'ensemble

Le système S.H.O.S peut recevoir les données de TOUS les capteurs de votre téléphone:

- 📍 **GPS** (Latitude, Longitude, Précision)
- ⚡ **Accélération** (X, Y, Z en m/s²)
- 🔄 **Gyroscope** (Rotation en °/s)
- 🔋 **Batterie** (Pourcentage)
- 💡 **Luminosité** (Lux)
- 👆 **Proximité** (Distance en cm)
- 🎤 **Microphone** (Niveau sonore)
- 🌡️ **Température** (si capteur présent)
- 📊 **Pression** (si capteur présent)

---

## ✅ Activation dans l'interface web

### Méthode simple (Recommandé)

1. Ouvrir: http://localhost:5000/mobile
2. Cliquer: **"Activer les capteurs"**
3. Accepter les permissions du navigateur
4. Les données s'envoient automatiquement

Les données sont visibles en temps réel dans le dashboard.

---

## 🔧 Intégration personnalisée

Si vous développez votre propre application web:

### HTML - Formulaire d'activation

```html
<button onclick="activateSensors()">
  ✅ Activer les capteurs
</button>

<div id="sensor-data">
  <p>GPS: <span id="gps">--</span></p>
  <p>Accélération: <span id="accel">--</span></p>
  <p>Batterie: <span id="battery">--</span>%</p>
</div>
```

### JavaScript - Activation complète

```javascript
// Initialiser Socket.IO
const socket = io('http://localhost:5000');

async function activateSensors() {
  try {
    // 1. GPS
    activateGPS();
    
    // 2. Mouvement (Accélération + Gyroscope)
    await activateMotion();
    
    // 3. Batterie
    activateBattery();
    
    // 4. Luminosité
    activateAmbientLight();
    
    console.log('✅ Tous les capteurs activés');
  } catch (error) {
    console.error('❌ Erreur:', error);
  }
}

// === GPS ===
function activateGPS() {
  if (!navigator.geolocation) {
    console.error('❌ GPS non supporté');
    return;
  }
  
  navigator.geolocation.watchPosition(
    (position) => {
      const { latitude, longitude, accuracy, altitude } = position.coords;
      const gpsData = {
        latitude: latitude.toFixed(6),
        longitude: longitude.toFixed(6),
        accuracy: accuracy.toFixed(2),
        altitude: altitude ? altitude.toFixed(2) : null
      };
      
      document.getElementById('gps').textContent = 
        `${gpsData.latitude}, ${gpsData.longitude}`;
      
      // Envoyer au serveur
      socket.emit('mobile_sensor', {
        type: 'gps',
        data: gpsData
      });
    },
    (error) => console.error('❌ Erreur GPS:', error),
    {
      enableHighAccuracy: true,
      timeout: 5000,
      maximumAge: 0
    }
  );
}

// === MOUVEMENT (Accélération + Gyroscope) ===
async function activateMotion() {
  if (!navigator.permissions) {
    console.error('❌ Permissions non supportées');
    return;
  }
  
  // iOS 13+ demande la permission
  if (typeof DeviceMotionEvent !== 'undefined' && 
      typeof DeviceMotionEvent.requestPermission === 'function') {
    try {
      const permission = await DeviceMotionEvent.requestPermission();
      if (permission !== 'granted') {
        throw new Error('Permission refusée');
      }
    } catch (error) {
      console.error('❌ Erreur permission:', error);
      return;
    }
  }
  
  window.addEventListener('devicemotion', (event) => {
    const accel = event.acceleration;
    const accelMagnitude = Math.sqrt(
      accel.x**2 + accel.y**2 + accel.z**2
    ).toFixed(2);
    
    const gyro = event.rotationRate;
    const gyroMagnitude = Math.sqrt(
      gyro.alpha**2 + gyro.beta**2 + gyro.gamma**2
    ).toFixed(2);
    
    const motionData = {
      acceleration: {
        x: accel.x.toFixed(2),
        y: accel.y.toFixed(2),
        z: accel.z.toFixed(2),
        magnitude: accelMagnitude
      },
      gyroscope: {
        alpha: gyro.alpha.toFixed(2),
        beta: gyro.beta.toFixed(2),
        gamma: gyro.gamma.toFixed(2),
        magnitude: gyroMagnitude
      }
    };
    
    document.getElementById('accel').textContent = accelMagnitude + ' m/s²';
    
    socket.emit('mobile_sensor', {
      type: 'motion',
      data: motionData
    });
  }, { passive: true });
}

// === BATTERIE ===
function activateBattery() {
  if (!navigator.getBattery && !navigator.battery) {
    console.warn('⚠️  API Batterie non supportée');
    return;
  }
  
  const battery = navigator.getBattery() || navigator.battery;
  
  if (!battery) return;
  
  const updateBatteryStatus = () => {
    const level = Math.round(battery.level * 100);
    const charging = battery.charging;
    const chargingTime = battery.chargingTime;
    const dischargingTime = battery.dischargingTime;
    
    document.getElementById('battery').textContent = level;
    
    socket.emit('mobile_sensor', {
      type: 'battery',
      data: {
        level: level,
        charging: charging,
        chargingTime: chargingTime,
        dischargingTime: dischargingTime
      }
    });
  };
  
  updateBatteryStatus();
  battery.addEventListener('chargingchange', updateBatteryStatus);
  battery.addEventListener('levelchange', updateBatteryStatus);
  battery.addEventListener('chargingtimechange', updateBatteryStatus);
  battery.addEventListener('dischargingtimechange', updateBatteryStatus);
}

// === LUMINOSITÉ ===
function activateAmbientLight() {
  if (!('AmbientLightSensor' in window)) {
    console.warn('⚠️  Capteur luminosité non supporté');
    return;
  }
  
  try {
    const sensor = new AmbientLightSensor();
    
    sensor.addEventListener('reading', () => {
      const illuminance = sensor.illuminance;
      
      socket.emit('mobile_sensor', {
        type: 'light',
        data: {
          illuminance: illuminance
        }
      });
    });
    
    sensor.addEventListener('error', (event) => {
      console.error('❌ Erreur capteur luminosité:', event.error);
    });
    
    sensor.start();
  } catch (error) {
    console.error('❌ Erreur initialisation luminosité:', error);
  }
}
```

---

## 📊 Format des données reçues

Chaque capteur envoie les données via Socket.IO dans ce format:

```json
{
  "type": "gps|motion|battery|light",
  "data": { /* données du capteur */ }
}
```

### Exemple - GPS
```json
{
  "type": "gps",
  "data": {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "accuracy": 10.5,
    "altitude": 45.2
  }
}
```

### Exemple - Motion
```json
{
  "type": "motion",
  "data": {
    "acceleration": {
      "x": 0.5,
      "y": 0.2,
      "z": 9.8,
      "magnitude": 9.81
    },
    "gyroscope": {
      "alpha": 0.1,
      "beta": 0.2,
      "gamma": 0.05,
      "magnitude": 0.22
    }
  }
}
```

### Exemple - Battery
```json
{
  "type": "battery",
  "data": {
    "level": 85,
    "charging": false,
    "chargingTime": 3600,
    "dischargingTime": 7200
  }
}
```

---

## 🌐 Recevoir les données côté serveur

Dans votre Python Flask:

```python
from flask_socketio import emit

@socketio.on('mobile_sensor')
def handle_mobile_sensor(data):
    """Recevoir les données des capteurs du téléphone"""
    sensor_type = data.get('type')
    sensor_data = data.get('data')
    
    logger.info(f"📱 Données {sensor_type}: {sensor_data}")
    
    # Publier sur MQTT
    mqtt_handler.client.publish(
        f"shos/mobile/{sensor_type}",
        json.dumps(sensor_data),
        qos=1
    )
    
    # Notifier les autres clients
    emit('mobile_update', {
        'type': sensor_type,
        'data': sensor_data
    })
```

---

## 🔐 Compatibilité navigateur

| Capteur | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| GPS | ✅ | ✅ | ✅ | ✅ |
| Accélération | ✅ | ✅ | ⚠️* | ✅ |
| Gyroscope | ✅ | ✅ | ⚠️* | ✅ |
| Batterie | ✅ | ⚠️ | ❌ | ✅ |
| Luminosité | ❌ | ❌ | ❌ | ❌ |

*iOS 13+: Demande permission explicite

---

## ⚠️ Permissions requises

Les données sensibles demandent une permission:

```javascript
// Déjà géré dans activateMotion()
const permission = await DeviceMotionEvent.requestPermission();
```

L'utilisateur doit accepter:
- 📍 Partager sa position (GPS)
- 🎤 Accès au microphone (son)
- 🔄 Accès aux capteurs de mouvement

---

## 📊 Cas d'usage

1. **Suivi de localisation** (GPS)
2. **Détection de mouvement** (Gyroscope + Accélération)
3. **Alarme de batterie faible** (Batterie)
4. **Ajustement éclairage** (Luminosité)
5. **Détection activité** (Accélération)
6. **Niveau de bruit ambiant** (Microphone)

---

## 🚀 Tests

Pour tester localement:

```javascript
// Simuler un GPS
socket.emit('mobile_sensor', {
  type: 'gps',
  data: {
    latitude: 48.8566,
    longitude: 2.3522,
    accuracy: 5,
    altitude: 45
  }
});

// Vérifier dans le dashboard
// Les données s'affichent en temps réel!
```

---

**Version 1.0 - 2026 📱✨**
