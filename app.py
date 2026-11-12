import os
import time
import threading
import queue
from datetime import datetime
from pathlib import Path

import cv2
from flask import Flask, Response, jsonify, render_template, send_from_directory
from ultralytics import YOLO

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

BASE_DIR = Path(__file__).resolve().parent
CAPTURE_DIR = BASE_DIR / "captures"
CAPTURE_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
MODEL_PATH = os.getenv("YOLO_MODEL", "yolov8n.pt")
CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.50"))
CAMERA_INDEX = 0  # Laptop's built-in webcam

model = None
model_lock = threading.Lock()
state_lock = threading.Lock()
camera = None
camera_thread = None
running = False
latest_jpeg = None
latest_frame = None
latest_detections = []
last_error = None
voice_enabled = True
announced_at = {}
speech_queue = queue.Queue(maxsize=20)
speech_thread = None
last_inference = 0.0
fps_value = 0.0


def get_model():
    global model
    with model_lock:
        if model is None:
            model = YOLO(MODEL_PATH)  # Downloads model weights on first run
    return model


def speech_worker():
    """Run text-to-speech away from the camera/inference thread."""
    if pyttsx3 is None:
        return
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        while True:
            phrase = speech_queue.get()
            if phrase is None:
                break
            try:
                engine.say(phrase)
                engine.runAndWait()
            except Exception as exc:
                print("Speech error:", exc)
    except Exception as exc:
        print("Text-to-speech initialization error:", exc)


def announce_objects(names):
    if not voice_enabled or pyttsx3 is None:
        return
    now = time.time()
    new_names = []
    for name in sorted(set(names)):
        # Avoid repeating the same object continuously.
        if now - announced_at.get(name, 0) >= 8:
            announced_at[name] = now
            new_names.append(name)
    if new_names:
        phrase = "Detected " + ", ".join(new_names)
        try:
            speech_queue.put_nowait(phrase)
        except queue.Full:
            pass


def camera_loop():
    global camera, running, latest_jpeg, latest_frame
    global latest_detections, last_error, last_inference, fps_value

    cap = cv2.VideoCapture(CAMERA_INDEX)
    # Request a modest resolution to improve performance on typical laptops.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        with state_lock:
            last_error = "Could not open laptop webcam. Check permissions and close other camera apps."
            running = False
        cap.release()
        return

    camera = cap
    previous_time = time.time()

    try:
        while True:
            with state_lock:
                if not running:
                    break

            ok, frame = cap.read()
            if not ok:
                with state_lock:
                    last_error = "The webcam stopped returning frames."
                time.sleep(0.1)
                continue

            try:
                detector = get_model()
                results = detector.predict(frame, conf=CONFIDENCE, verbose=False)
                result = results[0]
                annotated = result.plot()
                detections = []
                names = []

                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls[0].item())
                        confidence = float(box.conf[0].item())
                        label = detector.names.get(class_id, str(class_id))
                        detections.append({
                            "name": label,
                            "confidence": round(confidence * 100, 1)
                        })
                        names.append(label)

                now = time.time()
                elapsed = now - previous_time
                previous_time = now
                fps_value = (1.0 / elapsed) if elapsed > 0 else 0.0
                announce_objects(names)

                ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if ok:
                    with state_lock:
                        latest_jpeg = encoded.tobytes()
                        latest_frame = annotated.copy()
                        latest_detections = detections
                        last_error = None
                        last_inference = time.time()

            except Exception as exc:
                with state_lock:
                    last_error = f"Detection error: {exc}"
                time.sleep(0.2)
    finally:
        cap.release()
        with state_lock:
            camera = None
            running = False


def generate_frames():
    while True:
        with state_lock:
            frame = latest_jpeg
            active = running
        if frame is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        elif not active:
            time.sleep(0.1)
        else:
            time.sleep(0.03)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/start")
def start_detection():
    global running, camera_thread, last_error
    with state_lock:
        if running:
            return jsonify(ok=True, message="Detection is already running.")
        running = True
        last_error = None
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    return jsonify(ok=True, message="Starting laptop webcam...")


@app.post("/api/stop")
def stop_detection():
    global running
    with state_lock:
        running = False
    return jsonify(ok=True, message="Stopping detection...")


@app.get("/api/status")
def status():
    with state_lock:
        return jsonify({
            "running": running,
            "detections": latest_detections,
            "error": last_error,
            "fps": round(fps_value, 1),
            "voice_available": pyttsx3 is not None,
            "voice_enabled": voice_enabled
        })


@app.post("/api/voice")
def toggle_voice():
    global voice_enabled
    data = __import__("flask").request.get_json(silent=True) or {}
    voice_enabled = bool(data.get("enabled", True))
    return jsonify(ok=True, voice_enabled=voice_enabled)


@app.post("/api/capture")
def capture_image():
    with state_lock:
        frame = None if latest_frame is None else latest_frame.copy()
    if frame is None:
        return jsonify(ok=False, message="No frame available yet. Start detection first."), 400
    filename = "detection_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
    path = CAPTURE_DIR / filename
    if not cv2.imwrite(str(path), frame):
        return jsonify(ok=False, message="Could not save the image."), 500
    return jsonify(ok=True, filename=filename, message=f"Saved {filename}")


@app.get("/captures/<path:filename>")
def get_capture(filename):
    return send_from_directory(CAPTURE_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    if pyttsx3 is None:
        print("Voice announcements unavailable: install pyttsx3 and a system speech engine.")
    else:
        speech_thread = threading.Thread(target=speech_worker, daemon=True)
        speech_thread.start()
    print("Open http://127.0.0.1:5000 in your browser.")
    # use_reloader=False prevents duplicate camera/model threads during development.
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True, use_reloader=False)
