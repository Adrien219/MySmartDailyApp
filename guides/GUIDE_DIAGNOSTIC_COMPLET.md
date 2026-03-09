# 🔧 GUIDE DIAGNOSTIC COMPLET - MONITORING EN TEMPS RÉEL

## Accès à la page diagnostic

```
http://localhost:5000/diag
ou
http://<IP_ORDINATEUR>:5000/diag
```

---

## 📊 SECTIONS DU DIAGNOSTIC

### 1. 📡 MQTT Broker

**Affiche:**
- ✅ Status connexion
- Adresse du broker
- Topics actifs
- Débit de messages par seconde

**Interprétation:**
- 🟢 **ACTIF** = Mosquitto fonctionne correctement
- 🔴 **DÉCONNECTÉ** = Mosquitto n'est pas lancé
- ⚠️ **0 msg/sec** = Aucune donnée reçue

**Actions:**
```bash
# Si DÉCONNECTÉ, relancer Mosquitto
mosquitto

# Vérifier les topics
mosquitto_sub -t "shos/#" -v
```

---

### 2. 🔌 Hardware Arduino

**Affiche:**
- Status du port série
- Port détecté (COM3, COM4, /dev/ttyUSB0, etc.)
- Baud rate (115200)
- Dernière lecture

**Interprétation:**
- 🟢 **CONNECTÉ** = Arduino reçoit les données
- 🔴 **DÉCONNECTÉ** = Arduino déconnecté ou pas de données depuis 10s
- ⏱️ **Dernière lecture** = timestamp de la dernière donnée

**Actions:**
```bash
# Windows - Vérifier le port dans Gestionnaire des périphériques
# Cherchez: COM3, COM4, COM5, etc.

# Linux - Vérifier les ports
ls /dev/tty*
dmesg | tail  # Voir la dernière ligne Arduino

# Test direct
python
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200)
print(ser.readline())  # Doit afficher un JSON
```

---

### 3. ⚙️ Backbone Kernel

**Affiche:**
- Status du kernel
- Uptime (temps de fonctionnement)
- Status normalisation
- Nombre d'alertes détectées

**Interprétation:**
- 🟢 **ACTIF** = Backbone en cours d'exécution
- ⏱️ **Uptime** = Depuis combien de temps il fonctionne
- 🚨 **Alertes** = Nombre total d'alertes détectées

**Actions:**
```bash
# Si ARRÊTÉ, relancer le backbone
python backbone_ultimate.py

# Vérifier les alertes
mosquitto_sub -t "shos/alert/#" -v
```

---

### 4. 🌐 Flask Server

**Affiche:**
- Status du serveur (toujours ACTIF)
- URL accessible
- Nombre de clients Socket.IO
- Latence de communication

**Interprétation:**
- 🟢 **ACTIF** = Flask fonctionne
- **Clients** = Nombre de navigateurs/appareils connectés
- ⏱️ **Latence** = Temps aller-retour Socket.IO (< 50ms = bon)

**Actions:**
```bash
# Si latence > 200ms, il y a un problème réseau
# Vérifier la connexion Internet
# Redémarrer Flask si besoin
```

---

### 5. 🌡️ Capteurs Arduino

**Affiche:**
- Température (°C)
- Humidité (%)
- Gaz (ppm)
- Distance (cm)

**Interprétation:**
- `--` = Pas encore de données
- `0` ou valeurs bizarres = Arduino envoie des données mal formées
- Valeurs plausibles = Tout fonctionne ✅

**Plages normales:**
- Température: -20 à +50 °C
- Humidité: 0 à 100 %
- Gaz: 0 à 500+ ppm
- Distance: 0 à 400 cm

**Actions:**
```bash
# Vérifier les données brutes
mosquitto_sub -t "shos/sensors/raw" -v

# Vérifier les données normalisées
mosquitto_sub -t "shos/sensors/normalized" -v
```

---

### 6. 💻 Système Local

**Affiche:**
- CPU (%)
- RAM (%)
- Disque (%)
- Température CPU (°C)

**Interprétation:**
- CPU < 50% = Normal
- CPU > 80% = Vérifier les processus
- RAM < 75% = Normal
- RAM > 90% = Danger, redémarrer
- Disque > 90% = Nettoyer le disque
- Temp CPU > 85°C = Problème refroidissement

**Actions:**
```bash
# Vérifier les processus
top  # Linux
tasklist  # Windows
ps aux | sort -k3 -r | head  # Linux

# Nettoyer le disque
df -h  # Voir l'utilisation
rm -rf ~/.cache/*  # Nettoyer le cache
```

---

### 7. 🛰️ ESP32 Module

**Affiche:**
- Status connexion ESP32
- Signal WiFi (dBm)
- Mémoire libre (MB)
- Température CPU

**Interprétation:**
- 🟢 **CONNECTÉ** = ESP32 reçoit les données MQTT
- 🔴 **DÉCONNECTÉ** = ESP32 pas de données depuis 10s
- **WiFi Signal:**
  - `-50 dBm` = Excellent
  - `-70 dBm` = Bon
  - `-85 dBm` = Faible
  - `< -90 dBm` = Très faible
- **Mémoire:**
  - > 100 MB = Normal
  - < 50 MB = ESP32 surchargé

**Actions:**
```bash
# Vérifier les données ESP32
mosquitto_sub -t "shos/sensors/esp32" -v

# Redémarrer l'ESP32
# (Bouton Reset sur la carte)
```

---

### 8. 📱 Capteurs Téléphone

**Affiche:**
- Status connexion mobile
- GPS (latitude, longitude)
- Accélération (m/s²)
- Batterie (%)

**Interprétation:**
- 🟢 **CONNECTÉ** = Téléphone reçoit les données
- 🔴 **DÉCONNECTÉ** = Téléphone pas activé ou pas de données
- **GPS:**
  - `48.8566, 2.3522` = Données valides
  - `0, 0` = GPS non disponible
- **Batterie:**
  - > 20% = Normal
  - < 10% = Bientôt déchargé
  - "🔌" = En charge

**Actions:**
```bash
# Aller sur http://<IP>:5000/mobile
# Cliquer "Activer les capteurs"
# Accepter les permissions

# Vérifier les données
mosquitto_sub -t "shos/sensors/mobile" -v
```

---

### 9. 🚨 Alertes Actives

**Affiche:**
- Toutes les alertes en cours
- Type d'alerte
- Valeur déclenchée

**Types d'alertes:**
- 🔴 **CRITIQUE:** Gaz > 400 ppm, Flamme détectée
- 🟠 **AVERTISSEMENT:** Température > 50°C, Humidité < 20%

**Actions:**
```bash
# Écouter les alertes
mosquitto_sub -t "shos/alert/#" -v

# Les alertes disparaissent quand la condition n'est plus vraie
```

---

### 10. 📊 Logs du Système

**Affiche:**
- Historique de tous les événements
- Timestamps précis
- Code couleur:
  - 🟢 **Vert** = Succès/Info
  - 🟠 **Orange** = Avertissement
  - 🔴 **Rouge** = Erreur

**Types de logs:**
```
✅ Succès         - Connexion établie, données reçues
⚠️  Avertissement  - Timeout, reconnexion
❌ Erreur         - JSON invalide, port fermé
📊 Info           - Données affichées, débit
```

**Actions:**
```bash
# Effacer les logs
Cliquer: 🗑️ Effacer logs

# Exporter les logs (via DevTools)
F12 -> Console -> copier les logs
```

---

## 🔍 DÉBOGUER UN PROBLÈME

### Cas 1: Aucune donnée de capteurs

**Diagnostic:**
1. ✅ Vérifier MQTT Broker = ACTIF
2. ✅ Vérifier Hardware Arduino = CONNECTÉ
3. ✅ Vérifier Capteurs Arduino = valeurs affichées

**Solutions:**
```bash
# Si Arduino = DÉCONNECTÉ
python bridge_v2.py

# Si capteurs = "--"
mosquitto_sub -t "shos/sensors/raw" -v
# Doit afficher des données JSON

# Si MQTT = DÉCONNECTÉ
mosquitto
```

### Cas 2: Données Arduino mais pas affichées

**Diagnostic:**
1. ✅ Vérifier Backbone = ACTIF
2. ✅ Vérifier Flask = ACTIF

**Solutions:**
```bash
# Si Backbone = ARRÊTÉ
python backbone_ultimate.py

# Si Flask = ARRÊTÉ
python app_v3_complete.py

# Vérifier la normalisation
mosquitto_sub -t "shos/sensors/normalized" -v
```

### Cas 3: ESP32 ne s'affiche pas

**Diagnostic:**
1. ✅ Vérifier ESP32 module = CONNECTÉ
2. ✅ Vérifier Signal WiFi > -80 dBm

**Solutions:**
```bash
# Si ESP32 = DÉCONNECTÉ
# Redémarrer l'ESP32 (bouton Reset)
# Ou vérifier la connexion WiFi de l'ESP32

# Tester la connexion
ping 192.168.1.X  # IP de l'ESP32
```

### Cas 4: Téléphone ne s'active pas

**Diagnostic:**
1. ✅ Vérifier Capteurs Téléphone = CONNECTÉ
2. ✅ Vérifier que le téléphone est sur le même WiFi

**Solutions:**
```bash
# Aller sur http://<IP>:5000/mobile
# Cliquer "Activer les capteurs"
# Accepter les permissions (GPS, mouvement)

# Vérifier dans les logs
Les logs doivent afficher: "✅ Capteurs activés"
```

---

## ⏱️ INTERPRÉTATION TEMPS RÉEL

La page diagnostic **actualise automatiquement** chaque seconde:

```
🌡️ Capteurs Arduino
📡 MQTT Broker
💻 Système Local
🛰️ ESP32
📱 Téléphone
🚨 Alertes
```

### Actualiser manuellement

```
Cliquer: 🔄 Actualiser
```

### Tester la latence

La latence Socket.IO est testée toutes les 5 secondes:
- < 50 ms = 🟢 Excellent
- 50-100 ms = 🟡 Bon
- > 200 ms = 🔴 Problème réseau

---

## 📈 MÉTRIQUES IMPORTANTES

### MQTT Broker
- `>0 msg/sec` = Données reçues ✅

### Hardware Arduino
- Status = CONNECTÉ ✅
- Dernière lecture = < 10 secondes ✅

### Backbone Kernel
- Status = ACTIF ✅
- Normalisation = "OK" ✅

### Flask Server
- Clients > 0 = Connecté ✅
- Latence < 100 ms = Bon ✅

### Capteurs Arduino
- Température: -20 à +50°C
- Humidité: 0-100%
- Gaz: 0-500+ ppm
- Distance: 0-400 cm

### Système Local
- CPU < 80%
- RAM < 90%
- Disque < 90%
- Temp CPU < 85°C

---

## 🎯 CHECKLIST DIAGNOSTIC

Tous les indicateurs doivent être au vert:

- [ ] MQTT Broker = ACTIF
- [ ] Hardware Arduino = CONNECTÉ
- [ ] Backbone Kernel = ACTIF
- [ ] Flask Server = ACTIF
- [ ] Capteurs Arduino = valeurs visibles
- [ ] Système Local = sain
- [ ] ESP32 = CONNECTÉ (si utilisé)
- [ ] Téléphone = CONNECTÉ (si utilisé)
- [ ] Alertes = gérées correctement
- [ ] Latence < 100 ms

---

**Diagnostic V3 - Monitoring complet! 🚀**
