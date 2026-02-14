import cv2
import datetime


FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 20
CODEC = 'XVID'     
OUTPUT_FILE = "motion_recording.mp4"

MOTION_THRESHOLD = 5000    
RECORD_SECONDS_AFTER_MOTION = 5


cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

fourcc = cv2.VideoWriter_fourcc(*CODEC)

out = None
recording = False
motion_timer = 0

ret, prev_frame = cap.read()
prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

print("System Ready... Monitoring for motion.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    frame_diff = cv2.absdiff(prev_gray, gray)
    thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
    motion_pixels = cv2.countNonZero(thresh)

   
    if motion_pixels > MOTION_THRESHOLD:
        print("Motion Detected!")

        if not recording:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"motion_{timestamp}.avi"

            out = cv2.VideoWriter(filename, fourcc, FPS,
                                  (FRAME_WIDTH, FRAME_HEIGHT))
            recording = True

        motion_timer = RECORD_SECONDS_AFTER_MOTION * FPS

   
    if recording:
        out.write(frame)
        motion_timer -= 1

        if motion_timer <= 0:
            print("Recording stopped.")
            recording = False
            out.release()

    prev_gray = gray

 
    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if out:
    out.release()
cv2.destroyAllWindows()
