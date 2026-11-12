const video = document.getElementById("video");
const placeholder = document.getElementById("placeholder");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const captureBtn = document.getElementById("captureBtn");
const message = document.getElementById("message");
const statusPill = document.getElementById("statusPill");
const objectCount = document.getElementById("objectCount");
const fps = document.getElementById("fps");
const detectionList = document.getElementById("detectionList");
const voiceToggle = document.getElementById("voiceToggle");
const voiceNote = document.getElementById("voiceNote");

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: body ? JSON.stringify(body) : "{}"
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "Request failed");
  return data;
}

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  message.textContent = "Starting webcam and loading the detection model...";
  try {
    const data = await post("/api/start");
    video.src = `/video_feed?t=${Date.now()}`;
    placeholder.classList.add("hidden");
    message.textContent = data.message;
  } catch (error) {
    message.textContent = error.message;
    startBtn.disabled = false;
  }
});

stopBtn.addEventListener("click", async () => {
  try {
    await post("/api/stop");
    message.textContent = "Stopping camera...";
  } catch (error) {
    message.textContent = error.message;
  }
});

captureBtn.addEventListener("click", async () => {
  try {
    const data = await post("/api/capture");
    message.innerHTML = `${data.message} · <a href="/captures/${encodeURIComponent(data.filename)}">Download</a>`;
  } catch (error) {
    message.textContent = error.message;
  }
});

voiceToggle.addEventListener("change", async () => {
  try {
    await post("/api/voice", {enabled: voiceToggle.checked});
    voiceNote.textContent = voiceToggle.checked ? "Voice announcements enabled." : "Voice announcements muted.";
  } catch (error) {
    message.textContent = error.message;
  }
});

async function refreshStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();

    startBtn.disabled = data.running;
    stopBtn.disabled = !data.running;
    captureBtn.disabled = !data.running;
    statusPill.textContent = data.running ? "● RUNNING" : "● STOPPED";
    statusPill.classList.toggle("active", data.running);

    if (!data.running) {
      video.removeAttribute("src");
      placeholder.classList.remove("hidden");
    }

    objectCount.textContent = data.detections.length;
    fps.textContent = data.fps;
    detectionList.replaceChildren();

    if (!data.detections.length) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No objects detected in current frame";
      detectionList.appendChild(li);
    } else {
      data.detections.forEach(item => {
        const li = document.createElement("li");
        const name = document.createElement("span");
        const confidence = document.createElement("strong");
        name.textContent = item.name;
        confidence.textContent = `${item.confidence}%`;
        li.append(name, confidence);
        detectionList.appendChild(li);
      });
    }

    if (!data.voice_available) {
      voiceNote.textContent = "Voice library unavailable. Install pyttsx3 and a system speech engine.";
    }
    if (data.error) {
      message.textContent = data.error;
      startBtn.disabled = false;
    }
  } catch (error) {
    message.textContent = "Cannot reach the Flask server.";
  }
}
setInterval(refreshStatus, 700);
refreshStatus();
