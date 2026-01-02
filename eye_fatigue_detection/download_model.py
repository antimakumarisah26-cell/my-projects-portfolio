import cv2
import dlib
import requests
import bz2
from pathlib import Path
import time
from imutils import face_utils
from scipy.spatial import distance as dist
from datetime import datetime

# ---------------- Model Download ---------------- #
def download_model():
    model_path = Path(r"C:\Users\appru\PycharmProjects\PythonProject7\Model\shape_predictor_68_face_landmarks.dat")
    if model_path.exists():
        print(" Model file already exists!")
        return str(model_path)

    print("Downloading model file...")
    url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
    try:
        Path('Model').mkdir(exist_ok=True)
        response = requests.get(url)
        response.raise_for_status()
        decompressed_data = bz2.decompress(response.content)
        with open(model_path, 'wb') as f:
            f.write(decompressed_data)
        print("Model downloaded successfully!")
        return str(model_path)
    except Exception as e:
        print(f"Model download failed: {e}")
        return None

# ---------------- EAR Calculation ---------------- #
def EAR_cal(eye):
    v1 = dist.euclidean(eye[1], eye[5])
    v2 = dist.euclidean(eye[2], eye[4])
    h1 = dist.euclidean(eye[0], eye[3])
    ear = (v1 + v2) / (2.0 * h1)
    return ear

def put_text(image, text, position, color=(0, 0, 255), font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, thickness=2):
    cv2.putText(image, text, position, font, font_scale, color, thickness)

# ---------------- Main Program ---------------- #
model_path = download_model()
if not model_path:
    print("Cannot proceed without model file")
    exit()

print("Starting eye detection...")

# Initialize camera
cam = cv2.VideoCapture(0)
cv2.namedWindow("Eye Blink Detection - Fatigue Monitor", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Eye Blink Detection - Fatigue Monitor", 1280, 720)

# ---------------- Parameters ---------------- #
FATIGUE_DURATION_THRESHOLD = 1.5
FATIGUE_BLINK_FREQUENCY_THRESHOLD = 10
blink_thresh = 0.25

eye_closed = False
isFatigue = False
blink_count = 0
last_eye_closed_time = 0
ptime = 0

avg_values = []
timestamps = []

# Initialize detectors
detector = dlib.get_frontal_face_detector()
lm_model = dlib.shape_predictor(model_path)
(L_start, L_end) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(R_start, R_end) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

print("Camera starting... Press 'q' to quit")

while True:
    ret, frame = cam.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Calculate FPS
    ctime = time.time()
    fps = 1 / (ctime - ptime) if (ctime - ptime) > 0 else 0
    ptime = ctime

    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(img_gray)
    isFatigue = False

    for face in faces:
        x1, y1 = face.left(), face.top()
        x2, y2 = face.right(), face.bottom()
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        shapes = lm_model(img_gray, face)
        shape = face_utils.shape_to_np(shapes)

        lefteye = shape[L_start:L_end]
        righteye = shape[R_start:R_end]

        for Lpt, rpt in zip(lefteye, righteye):
            cv2.circle(frame, tuple(Lpt), 2, (0, 255, 255), -1)
            cv2.circle(frame, tuple(rpt), 2, (0, 255, 255), -1)

        left_EAR = EAR_cal(lefteye)
        right_EAR = EAR_cal(righteye)
        avg = (left_EAR + right_EAR) / 2
        avg_values.append(avg)
        timestamps.append(datetime.now())
        put_text(frame, f'EAR: {avg:.2f}', (x1, y1 - 10), (255, 255, 0))

        # ---------------- Blink & Fatigue Detection ---------------- #
        if avg < blink_thresh:
            if not eye_closed:
                eye_closed = True
                last_eye_closed_time = time.time()
        else:
            if eye_closed:
                eye_closed = False
                duration = time.time() - last_eye_closed_time
                if 0.1 < duration < 0.8:
                    blink_count += 1
                if duration > FATIGUE_DURATION_THRESHOLD:
                    isFatigue = True

        if blink_count >= FATIGUE_BLINK_FREQUENCY_THRESHOLD:
            isFatigue = True

    # ---------------- Display Info ---------------- #
    put_text(frame, f'FPS: {int(fps)}', (20, 30), (0, 255, 0))
    put_text(frame, f'Blinks: {blink_count}', (20, 60), (255, 0, 0))
    put_text(frame, f'Eye Closed: {"Yes" if eye_closed else "No"}', (20, 90), (0, 0, 255))
    if isFatigue:
        put_text(frame, "FATIGUE DETECTED!", (20, 120), (0, 0, 255), font_scale=1.2, thickness=3)
        put_text(frame, "TAKE A BREAK!", (20, 150), (0, 0, 255), font_scale=1, thickness=2)

    cv2.imshow("Eye Blink Detection - Fatigue Monitor", frame)

    key = cv2.waitKey(1)
    try:
        if cv2.getWindowProperty("Eye Blink Detection - Fatigue Monitor", cv2.WND_PROP_AUTOSIZE) < 0:
            break
    except cv2.error:
        break
    if key & 0xFF == ord('q'):
        break

# Cleanup
cam.release()
cv2.destroyAllWindows()
print(f"Session ended. Total blinks detected: {blink_count}")
