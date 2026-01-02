import cv2
import dlib
import time
import bz2
import urllib.request
from pathlib import Path
from imutils import face_utils
from scipy.spatial import distance as dist
import tkinter as tk
from tkinter import messagebox
import sys


# ================== CONFIGURATION ==================
MODEL_DIR = Path("Model")
MODEL_FILE = MODEL_DIR / "shape_predictor_68_face_landmarks.dat"
MODEL_URL = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"

BLINK_THRESHOLD = 0.25
BLINK_FRAMES = 3
MAX_BLINKS = 10

# ================== MODEL SETUP ==================
def setup_model():
    """Check if model exists, if not download & extract it"""
    if MODEL_FILE.exists():
        print("Model already exists. Skipping download.")
        return True

    print("Model not found. Downloading...")
    try:
        MODEL_DIR.mkdir(exist_ok=True)
        
        print("Downloading model (38MB)... Please wait...")
        with urllib.request.urlopen(MODEL_URL) as response:
            file_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            data = b''
            
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data += chunk
                downloaded += len(chunk)
                percent = (downloaded * 100) // file_size if file_size else 0
                sys.stdout.write(f"\rDownloading: {percent}%")
                sys.stdout.flush()
        
        print("\nExtracting model...")
        decompressed_data = bz2.decompress(data)

        with open(MODEL_FILE, 'wb') as f:
            f.write(decompressed_data)

        print("Model downloaded and extracted successfully!")
        return True
    except Exception as e:
        print(f"Model download failed: {e}")
        return False

# ================== EAR FUNCTION ==================
def EAR_cal(eye):
    v1 = dist.euclidean(eye[1], eye[5])
    v2 = dist.euclidean(eye[2], eye[4])
    h1 = dist.euclidean(eye[0], eye[3])
    return (v1 + v2) / (2.0 * h1)

# ================== ALERT POPUP ==================
def show_alert():
    response = messagebox.askyesno(
        "Eye Fatigue Alert",
        f"⚠️ {MAX_BLINKS} blinks detected!\n\nEye fatigue detected.\n\n"
        "Click Yes to exit.\nClick No to continue monitoring."
    )
    return response

# ================== MAIN PROGRAM ==================
def main():
    # Tkinter setup
    root = tk.Tk()
    root.withdraw()

    # Load detectors
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(str(MODEL_FILE))

    (L_start, L_end) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
    (R_start, R_end) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

    # Initialize camera
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Error: Could not open camera")
        return

    # Get frame dimensions
    frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Calculate center position for face
    center_x = frame_width // 2
    center_y = frame_height // 2

    # Variables
    blink_count = 0
    frame_count = 0
    msg_shown = False
    ptime = 0
    show_landmarks = True

    print("="*50)
    print("EYE FATIGUE DETECTION SYSTEM")
    print("="*50)
    print("Instructions:")
    print("1. Sit facing the camera")
    print("2. Blink naturally")
    print("3. Press 'r' to reset counter")
    print("4. Press 't' to toggle eye landmarks")
    print("5. Press 'q' to quit")
    print("="*50)
    print("\nStarting detection...")

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)

        # FPS calculation
        ctime = time.time()
        fps = int(1 / (ctime - ptime)) if (ctime - ptime) > 0 else 0
        ptime = ctime

        face_detected = len(faces) > 0
        avg_EAR = 0.0
        face_center_x, face_center_y = 0, 0

        if face_detected:
            face = faces[0]
            shape = predictor(gray, face)
            shape = face_utils.shape_to_np(shape)

            left_eye = shape[L_start:L_end]
            right_eye = shape[R_start:R_end]

            left_EAR = EAR_cal(left_eye)
            right_EAR = EAR_cal(right_eye)
            avg_EAR = (left_EAR + right_EAR) / 2.0

            # Calculate face center for guidance
            face_center_x = (face.left() + face.right()) // 2
            face_center_y = (face.top() + face.bottom()) // 2

            # Draw eye landmarks if enabled
            if show_landmarks:
                for (x, y) in left_eye:
                    cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)
                for (x, y) in right_eye:
                    cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)

            # Blink detection
            if avg_EAR < BLINK_THRESHOLD:
                frame_count += 1
            else:
                if frame_count >= BLINK_FRAMES:
                    blink_count += 1
                    print(f"Blink #{blink_count} detected")

                    if blink_count >= MAX_BLINKS and not msg_shown:
                        msg_shown = True
                        # Show warning on screen
                        cv2.putText(frame, "FATIGUE ALERT!", (center_x - 100, 50), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                        cv2.imshow("Eye Fatigue Detection", frame)
                        cv2.waitKey(1000)
                        
                        if show_alert():
                            print("User chose to exit")
                            break
                        else:
                            print("User chose to continue")
                            blink_count = 0
                            msg_shown = False

                frame_count = 0

        # ============ DISPLAY INFO ============
        # Top bar - Yeh ab blink status ke liye use hoga
        top_bar_height = 80
        cv2.rectangle(frame, (0, 0), (frame_width, top_bar_height), (40, 40, 40), -1)
        
                # ============ BLINK STATUS (TOP BAR) ============
        # FPS (top left)
        cv2.putText(frame, f"FPS: {fps}", (20, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # EAR (right side - left part)
        cv2.putText(frame, f"EAR: {avg_EAR:.3f}", (frame_width - 300, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Blink count (right side - right part)
        blink_color = (0, 255, 0)
        if blink_count >= MAX_BLINKS * 0.6:
            blink_color = (0, 165, 255)
        if blink_count >= MAX_BLINKS:
            blink_color = (0, 0, 255)
            
        cv2.putText(frame, f"Blinks: {blink_count}/{MAX_BLINKS}", 
                   (frame_width - 150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, blink_color, 2)
        
        # Color indicator circle (blink ke saath)
        circle_x = frame_width - 50
        circle_y = 55  # Same y as blink text
        cv2.circle(frame, (circle_x, circle_y), 8, blink_color, -1)
        cv2.circle(frame, (circle_x, circle_y), 8, (255, 255, 255), 1)
      
        # Face detection status (below top bar)
        status_y = top_bar_height + 40
        if not face_detected:
            cv2.putText(frame, "NO FACE DETECTED", (center_x - 100, status_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        else:
            cv2.putText(frame, "FACE DETECTED", (center_x - 80, status_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # ============ PROGRESS BAR (TOP BAR) ============
        bar_width = 200
        bar_height = 15
        bar_x = center_x - bar_width // 2
        bar_y = 50
        
        # Progress bar background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (100, 100, 100), -1)
        
        # Progress
        progress = min(blink_count / MAX_BLINKS, 1.0)
        progress_width = int(bar_width * progress)
        
        # Color based on progress
        if progress < 0.6:
            bar_color = (0, 255, 0)  # Green
        elif progress < 0.9:
            bar_color = (0, 165, 255)  # Orange
        else:
            bar_color = (0, 0, 255)  # Red
            
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), 
                     bar_color, -1)
        
        # Border
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (255, 255, 255), 1)
        
        # Percentage text
        cv2.putText(frame, f"{int(progress*100)}%", (bar_x + bar_width + 10, bar_y + 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # ============ BOTTOM INSTRUCTIONS ============
        bottom_bar_y = frame_height - 60
        cv2.rectangle(frame, (0, bottom_bar_y), (frame_width, frame_height), (30, 30, 30), -1)
        cv2.putText(frame, "Press 'q': Quit  |  'r': Reset  |  't': Toggle landmarks", 
                   (10, frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # ============ SHOW AND CENTER WINDOW ============
        cv2.imshow("Eye Fatigue Detection", frame)
        
        # Get screen dimensions
        screen_width = 1366  # Adjust to your screen resolution
        screen_height = 768  # Adjust to your screen resolution
        
        # Calculate center position (DIFFERENT VARIABLE NAME)
        win_x = (screen_width - frame_width) // 2
        win_y = (screen_height - frame_height) // 2
        
        # Move window to center
        cv2.moveWindow("Eye Fatigue Detection", win_x, win_y)

        # ============ KEYBOARD CONTROLS ============
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("Quitting...")
            break
        elif key == ord('r'):
            blink_count = 0
            msg_shown = False
            print("Counter reset!")
        elif key == ord('t'):
            show_landmarks = not show_landmarks
            print(f"Eye landmarks: {'ON' if show_landmarks else 'OFF'}")

    # Cleanup
    cam.release()
    cv2.destroyAllWindows()
    root.destroy()
    print("\nApplication closed successfully!")

# ================== ENTRY POINT ==================
if __name__ == "__main__":
    print("Initializing Eye Fatigue Detection System...")
    if setup_model():
        main()
    else:
        print("Cannot start application without model")
        print("Please check your internet connection and try again")
        input("Press Enter to exit...")