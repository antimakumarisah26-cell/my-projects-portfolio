import cv2
import dlib
import time
from imutils import face_utils
from scipy.spatial import distance as dist
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# ========== VARIABLES ==========
blink_thresh = 0.25
blink_count = 0
count = 0
msg_shown = False

# ========== LOAD MODEL ==========
model_file = Path(r'C:\Users\appru\OneDrive\Desktop\eye_fatigue_detection\Model\shape_predictor_68_face_landmarks.dat')

if not model_file.exists():
    print("Error: Model file not found!")
    exit()

detector = dlib.get_frontal_face_detector()
lm_model = dlib.shape_predictor(str(model_file))
(L_start, L_end) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(R_start, R_end) = face_utils.FACIAL_LANDMARKS_IDXS['right_eye']

# ========== FUNCTIONS ==========
def EAR_cal(eye):
    v1 = dist.euclidean(eye[1], eye[5])
    v2 = dist.euclidean(eye[2], eye[4])
    h1 = dist.euclidean(eye[0], eye[3])
    return (v1 + v2) / (2.0 * h1)

def show_alert():
    global msg_shown, blink_count
    
    response = messagebox.askokcancel(
        "Eye Fatigue Alert", 
        "10 blinks detected. Eye fatigue detected.\n\nClick OK to stop application.\nClick Cancel to continue."
    )
    
    if response:  # OK clicked
        return True  # Stop application
    else:  # Cancel clicked
        blink_count = 0
        msg_shown = False
        return False  # Continue

# ========== MAIN CODE ==========
# Tkinter setup
root = tk.Tk()
root.withdraw()

# Start camera
cam = cv2.VideoCapture(0)
ptime = 0

while True:
    ret, frame = cam.read()
    if not ret:
        break
    
    # Mirror effect
    frame = cv2.flip(frame, 1)
    
    # Calculate FPS
    ctime = time.time()
    fps = int(1 / (ctime - ptime)) if (ctime - ptime) > 0 else 0
    ptime = ctime
    
    # Display FPS
    cv2.putText(frame, f'FPS: {fps}', (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Process frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)
    
    for face in faces:
        shapes = lm_model(gray, face)
        shape = face_utils.shape_to_np(shapes)
        
        lefteye = shape[L_start:L_end]
        righteye = shape[R_start:R_end]
        
        if len(lefteye) == 6 and len(righteye) == 6:
            left_EAR = EAR_cal(lefteye)
            right_EAR = EAR_cal(righteye)
            avg = (left_EAR + right_EAR) / 2.0
            
            # Blink detection
            if avg < blink_thresh:
                count += 1
            else:
                if count >= 3:  # tt_frame = 3
                    blink_count += 1
                    
                    # Show alert after 10 blinks
                    if blink_count >= 10 and not msg_shown:
                        msg_shown = True
                        should_stop = show_alert()
                        
                        if should_stop:
                            cam.release()
                            cv2.destroyAllWindows()
                            root.destroy()
                            exit()
                
                count = 0
    
    # Display blink count
    cv2.putText(frame, f'Blinks: {blink_count}/10', (20, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Instructions
    cv2.putText(frame, "Press 'q' to quit", (20, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    cv2.imshow("Eye Fatigue Detection", frame)
    
    # Exit conditions
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    if cv2.getWindowProperty("Eye Fatigue Detection", cv2.WND_PROP_VISIBLE) < 1:
        break

# Cleanup
cam.release()
cv2.destroyAllWindows()
root.destroy()
print("Application closed.")