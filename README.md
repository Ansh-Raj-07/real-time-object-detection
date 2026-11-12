# AI Real-Time Object Detection Web Application

A local Flask web application that uses a laptop webcam, OpenCV and Ultralytics YOLO to detect objects in real time. It includes a browser dashboard, object counts, confidence scores, voice announcements and annotated snapshot saving.

## Features

- Live laptop webcam stream (camera index `0`)
- YOLO object detection with bounding boxes and confidence scores
- Object list, count and approximate processing FPS
- Optional voice announcements using `pyttsx3`
- Save annotated snapshots in `captures/`
- Responsive browser interface

## Requirements

- Python 3.9 or newer (Python 3.10/3.11 recommended)
- Laptop webcam
- Internet connection for the first YOLO model download
- Windows, macOS or Linux

## Setup

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Press **Start Detection**. The first launch downloads `yolov8n.pt`; allow it to finish. Click **Stop** to release the webcam.

## Voice announcements

Voice is enabled by default. The app announces newly detected object names and throttles repeat announcements to one per object every 8 seconds.

`pyttsx3` requires a system speech engine:
- Windows: SAPI5 is normally available.
- macOS: built-in `NSSpeechSynthesizer` is normally available.
- Linux: install eSpeak, for example `sudo apt install espeak-ng` (package name varies by distribution).

If speech setup fails, visual detection still works. Check the terminal for the speech error.

## Configuration

Set environment variables before running:

```bash
YOLO_MODEL=yolov8n.pt
YOLO_CONFIDENCE=0.50
```

For Windows PowerShell:

```powershell
$env:YOLO_CONFIDENCE="0.60"
python app.py
```

The default model is the small, fast `yolov8n.pt`. A compatible Ultralytics detection model can be selected with `YOLO_MODEL`.

## Project structure

```text
real_time_object_detection_flask/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   └── style.css
└── captures/             # Created automatically
```

## Troubleshooting

- **Camera will not open:** close Zoom/Meet/Camera apps, check OS camera permissions, then restart the Flask app.
- **Black video:** ensure the webcam works in the operating system's camera application.
- **Slow detection:** use `yolov8n.pt`, reduce webcam resolution in `app.py`, or use a machine with a supported GPU.
- **No voice:** install the OS speech engine listed above and verify `pyttsx3` is installed in the active virtual environment.
- **Model download issue:** check internet access and try launching again.
- **Port 5000 busy:** change `port=5000` in the final `app.run(...)` line to another available port, such as `5001`.

## Privacy and security

This is intended for local educational use. The server binds to `127.0.0.1`, so it is accessible only from the same computer by default. Camera frames are processed locally and are not intentionally uploaded. Snapshots are saved locally in `captures/`. Do not expose the development server to the public internet without adding authentication, HTTPS and appropriate security controls.

## Note

YOLO's pretrained COCO model recognizes common object categories; it does not identify every possible object or person by identity. Detection accuracy depends on lighting, camera quality, object size and model confidence threshold.
