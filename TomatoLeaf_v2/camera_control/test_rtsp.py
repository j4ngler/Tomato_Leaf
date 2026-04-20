import cv2
from urllib.parse import quote

# Luu y: encode password de tranh truong hop mat khau chua ky tu dac biet
user = "admin"
pwd = "UIZCHI"
pwd_enc = quote(pwd, safe="")

url = f"rtsp://{user}:{pwd_enc}@192.168.1.57:554/cam/realmonitor?channel=1&subtype=0"
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
if not cap.isOpened():
    raise RuntimeError("Khong mo duoc RTSP. Kiem tra URL/user/password/stream path.")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        # Neu camera tu choi (401) hoac chua san sang, tiep tuc loat ung de tranh crash
        continue

    frame = cv2.resize(frame, (640, 480))
    cv2.imshow("Original", frame)

    if cv2.waitKey(1) & 0xff == ord('q'):
        break

cv2.destroyAllWindows()
cap.release()