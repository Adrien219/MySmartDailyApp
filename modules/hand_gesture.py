import cv2
import mediapipe as mp
import time

class PiHandController:
    def __init__(self, cam_index=0):
        # Initialisation de la caméra locale (0 pour la Pi Cam ou USB)
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        
        # Pour éviter les déclenchements accidentels
        self.last_gesture = "NONE"
        self.gesture_start_time = 0
        self.confirm_threshold = 0.5 # Secondes

    def get_stable_gesture(self):
        ret, frame = self.cap.read()
        if not ret: return "ERROR", None

        current_gesture = "NONE"
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)

        if results.multi_hand_landmarks:
            # --- Logique de détection des doigts ---
            # (Identique au module précédent : pouce, index, etc.)
            lms = results.multi_hand_landmarks[0].landmark
            
            # Calcul des doigts levés
            fingers = []
            # Pouce (comparaison horizontale/verticale selon l'orientation)
            fingers.append(lms[4].y < lms[3].y) 
            # Les 4 autres doigts
            for tip in [8, 12, 16, 20]:
                fingers.append(lms[tip].y < lms[tip-2].y)

            # --- Mapping des Gestes ---
            if fingers == [True, False, False, False, False]: current_gesture = "TRIGGER_FLORENCE"
            elif fingers == [True, True, True, True, True]:   current_gesture = "START_SYSTEM"
            elif fingers == [False, False, False, False, False]: current_gesture = "STOP_SYSTEM"
            elif fingers == [False, True, False, False, False]:  current_gesture = "READ_TEXT"

        # --- Logique de confirmation (Debounce) ---
        if current_gesture == self.last_gesture and current_gesture != "NONE":
            if (time.time() - self.gesture_start_time) > self.confirm_threshold:
                return current_gesture, frame
        else:
            self.last_gesture = current_gesture
            self.gesture_start_time = time.time()

        return "NONE", frame

    def release(self):
        self.cap.release()
