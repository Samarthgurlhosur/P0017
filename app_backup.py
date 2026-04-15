from flask import Flask, render_template_string, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import base64
import threading
import json
import os
from datetime import datetime
import image as detection_module
from werkzeug.utils import secure_filename
from PIL import Image
import io

app = Flask(__name__)
app.secret_key = "xray-scanner-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*")

# Upload configuration
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "mp4", "avi"}

# Global variables
detection_results = []
threat_log = []
scanning = False

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔍 X-RAY THREAT SCANNER - Security Screening System</title>
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <style>
            :root {
                --primary: #00d4ff;
                --primary-dark: #0088cc;
                --danger: #ff3333;
                --warning: #ffaa00;
                --success: #00ff88;
                --dark-bg: #0a0e27;
                --card-bg: #1a1f3a;
                --text-light: #e0e0e0;
                --text-muted: #888;
            }
            
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, var(--dark-bg) 0%, #0f1629 100%);
                color: var(--text-light);
                overflow-x: hidden;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            header {
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid var(--primary);
                padding-bottom: 20px;
            }
            
            h1 {
                font-size: 2.5em;
                color: var(--primary);
                text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
                margin-bottom: 10px;
            }
            
            .subtitle {
                color: var(--text-muted);
                font-size: 1.1em;
            }
            
            .dashboard {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }
            
            @media (max-width: 1024px) {
                .dashboard { grid-template-columns: 1fr; }
            }
            
            .card {
                background: linear-gradient(135deg, var(--card-bg) 0%, rgba(26, 31, 58, 0.8) 100%);
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            }
            
            .camera-section {
                position: relative;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
            }
            
            #camera-feed {
                width: 100%;
                height: 400px;
                background: #000;
                border-radius: 8px;
                object-fit: cover;
                display: none;
            }
            
            .camera-placeholder {
                width: 100%;
                height: 400px;
                background: radial-gradient(circle, rgba(0,212,255,0.1) 0%, transparent 70%);
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                border: 2px dashed var(--primary);
                color: var(--text-muted);
                font-size: 1.1em;
            }
            
            .controls {
                display: flex;
                gap: 10px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            
            button {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 1em;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                color: #000;
                box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
            }
            
            .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6); }
            .btn-primary:active { transform: translateY(0); }
            
            .btn-danger {
                background: var(--danger);
                color: white;
            }
            
            .btn-danger:hover { background: #ff5555; }
            
            .btn-success {
                background: var(--success);
                color: #000;
            }
            
            .detection-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
            }
            
            .detection-item {
                background: rgba(0, 212, 255, 0.1);
                border: 2px solid var(--primary);
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                animation: slideIn 0.3s ease;
            }
            
            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .detection-item.critical {
                border-color: var(--danger);
                background: rgba(255, 51, 51, 0.1);
            }
            
            .detection-item.warning {
                border-color: var(--warning);
                background: rgba(255, 170, 0, 0.1);
            }
            
            .item-name {
                font-weight: bold;
                font-size: 1.2em;
                margin-bottom: 5px;
            }
            
            .item-severity {
                font-size: 0.9em;
                padding: 5px 10px;
                border-radius: 4px;
                display: inline-block;
                background: rgba(0, 0, 0, 0.3);
            }
            
            .item-severity.critical { color: var(--danger); }
            .item-severity.warning { color: var(--warning); }
            .item-severity.info { color: var(--primary); }
            
            .status-badge {
                display: inline-block;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                margin: 5px 0;
            }
            
            .status-active { background: var(--success); color: #000; }
            .status-inactive { background: var(--text-muted); color: #000; }
            .status-threat { background: var(--danger); color: white; }
            
            .threat-log {
                background: rgba(0, 0, 0, 0.3);
                border-left: 4px solid var(--primary);
                border-radius: 4px;
                padding: 15px;
                margin: 10px 0;
                max-height: 300px;
                overflow-y: auto;
            }
            
            .threat-entry {
                padding: 10px;
                border-bottom: 1px solid rgba(0, 212, 255, 0.1);
                font-size: 0.9em;
            }
            
            .threat-entry:last-child { border-bottom: none; }
            
            .threat-time {
                color: var(--text-muted);
                font-size: 0.8em;
            }
            
            .threat-item {
                color: var(--primary);
                font-weight: bold;
            }
            
            .threat-item.critical { color: var(--danger); }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin: 15px 0;
            }
            
            .stat {
                background: rgba(0, 212, 255, 0.1);
                border: 1px solid var(--primary);
                border-radius: 8px;
                padding: 15px;
                text-align: center;
            }
            
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: var(--primary);
            }
            
            .stat-label {
                font-size: 0.9em;
                color: var(--text-muted);
                margin-top: 5px;
            }
            
            .upload-section {
                border: 2px dashed var(--primary);
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .upload-section:hover {
                background: rgba(0, 212, 255, 0.1);
            }
            
            #file-input { display: none; }
            
            .spinner {
                border: 4px solid rgba(0, 212, 255, 0.2);
                border-top: 4px solid var(--primary);
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🔍 X-RAY THREAT SCANNER</h1>
                <p class="subtitle">Real-time Security Screening System | Detect Suspicious Items via Camera</p>
            </header>
            
            <div class="dashboard" style="grid-template-columns: 1fr 1fr;">
                <!-- Normal Camera Feed Section -->
                <div class="card">
                    <h2 style="margin-bottom: 15px; color: var(--primary);">📹 NORMAL CAMERA</h2>
                    <div class="camera-section">
                        <video id="camera-feed" playsinline autoplay muted></video>
                        <div class="camera-placeholder" id="placeholder-normal">
                            <span>📷 No camera active</span>
                        </div>
                    </div>
                </div>
                
                <!-- X-Ray Camera Feed Section -->
                <div class="card">
                    <h2 style="margin-bottom: 15px; color: #00ff00;">🔍 X-RAY SCANNER (Real-time)</h2>
                    <div class="camera-section">
                        <canvas id="canvas-xray" style="width:100%; height:400px; background:#000; border-radius:8px;"></canvas>
                        <div class="camera-placeholder" id="placeholder-xray">
                            <span>🔎 X-ray scan pending</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Controls -->
            <div class="card" style="margin-top: 20px;">
                <div style="display: flex; gap: 15px; flex-wrap: wrap; align-items: center; justify-content: center;">
                    <button class="btn-primary" id="start-btn" style="padding: 15px 30px; font-size: 1.1em;">▶ START DUAL SCANNING</button>
                    <button class="btn-danger" id="stop-btn" style="display:none; padding: 15px 30px; font-size: 1.1em;">⏹ STOP SCANNING</button>
                    <div class="stats-grid" style="flex: 1; min-width: 300px; margin: 0;">
                        <div class="stat">
                            <div class="stat-value" id="threat-count">0</div>
                            <div class="stat-label">Threats Detected</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" id="scan-status">IDLE</div>
                            <div class="stat-label">Status</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" id="frame-count">0</div>
                            <div class="stat-label">Frames Scanned</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Detection Results Section -->
            <div class="card" style="margin-top: 20px;">
                <h2 style="margin-bottom: 15px; color: var(--primary);">⚠️ REAL-TIME THREAT DETECTION</h2>
                <div id="detections" class="detection-grid">
                    <p style="color: var(--text-muted); text-align: center; grid-column: 1/-1;">✓ Scan for threats</p>
                </div>
            </div>
            
            <!-- Threat Log Section -->
            <div class="card">
                <h2 style="margin-bottom: 15px; color: var(--primary);">📋 THREAT LOG</h2>
                <div class="threat-log" id="threat-log">
                    <p style="color: var(--text-muted); text-align: center;">No threats logged yet</p>
                </div>
            </div>
            
            <!-- Upload Section -->
            <div class="card" style="margin-top: 20px;">
                <h2 style="margin-bottom: 15px; color: var(--primary);">📤 SCAN IMAGE FILE</h2>
                <div class="upload-section" id="upload-area">
                    <p>📁 Click to upload or drag & drop an image/video file</p>
                    <p style="font-size: 0.9em; color: var(--text-muted);">Supported formats: JPG, PNG, GIF</p>
                </div>
                <input type="file" id="file-input" accept="image/*,video/*">
            </div>
        </div>
        
        <script>
            const socket = io();
            let stream = null;
            let scanning = false;
            let frameCount = 0;
            
            // DOM Elements
            const startBtn = document.getElementById('start-btn');
            const stopBtn = document.getElementById('stop-btn');
            const videoFeed = document.getElementById('camera-feed');
            const canvasXray = document.getElementById('canvas-xray');
            const xrayCtx = canvasXray.getContext('2d');
            const placeholderNormal = document.getElementById('placeholder-normal');
            const placeholderXray = document.getElementById('placeholder-xray');
            const threatCountEl = document.getElementById('threat-count');
            const scanStatusEl = document.getElementById('scan-status');
            const frameCountEl = document.getElementById('frame-count');
            const detectionsEl = document.getElementById('detections');
            const threatLogEl = document.getElementById('threat-log');
            const uploadArea = document.getElementById('upload-area');
            const fileInput = document.getElementById('file-input');
            
            // Setup Canvas for X-Ray display
            function setupCanvasSize() {
                if (videoFeed.videoWidth > 0) {
                    canvasXray.width = videoFeed.videoWidth;
                    canvasXray.height = videoFeed.videoHeight;
                }
            }
            
            // Start Dual Camera Scanning
            startBtn.addEventListener('click', async () => {
                try {
                    stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
                    });
                    
                    videoFeed.srcObject = stream;
                    videoFeed.style.display = 'block';
                    placeholderNormal.style.display = 'none';
                    placeholderXray.style.display = 'none';
                    canvasXray.style.display = 'block';
                    
                    scanning = true;
                    frameCount = 0;
                    
                    startBtn.style.display = 'none';
                    stopBtn.style.display = 'inline-block';
                    scanStatusEl.textContent = 'ACTIVE';
                    scanStatusEl.style.color = 'var(--success)';
                    
                    // Wait for video to load
                    setTimeout(() => {
                        setupCanvasSize();
                        captureFrames();
                    }, 500);
                } catch (err) {
                    alert('Camera access denied. Please enable camera permissions.');
                    console.error(err);
                }
            });
            
            // Stop Dual Camera Scanning
            stopBtn.addEventListener('click', () => {
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                
                videoFeed.style.display = 'none';
                canvasXray.style.display = 'none';
                placeholderNormal.style.display = 'flex';
                placeholderXray.style.display = 'flex';
                scanning = false;
                
                startBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
                scanStatusEl.textContent = 'IDLE';
                scanStatusEl.style.color = 'var(--warning)';
            });
            
            // Apply X-Ray Effect to Canvas
            function applyXrayEffect(imageData) {
                const data = imageData.data;
                
                // Convert to grayscale and apply edge detection effect
                for (let i = 0; i < data.length; i += 4) {
                    const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
                    
                    // Invert for X-ray effect
                    const inverted = 255 - gray;
                    
                    data[i] = Math.max(0, inverted * 0.3);     // Red - reduce
                    data[i + 1] = Math.min(255, inverted * 1.3); // Green - enhance
                    data[i + 2] = Math.max(0, inverted * 0.5);  // Blue - reduce
                    data[i + 3] = 255;  // Alpha
                }
                
                return imageData;
            }
            
            // Continuous Frame Capture & Dual Display
            function captureFrames() {
                if (!scanning) return;
                
                try {
                    // Draw normal camera feed
                    if (videoFeed.videoWidth > 0 && videoFeed.videoHeight > 0) {
                        // Draw to X-ray canvas with effect
                        const tempCanvas = document.createElement('canvas');
                        tempCanvas.width = videoFeed.videoWidth;
                        tempCanvas.height = videoFeed.videoHeight;
                        const tempCtx = tempCanvas.getContext('2d');
                        tempCtx.drawImage(videoFeed, 0, 0);
                        
                        // Get image data and apply X-ray effect
                        let imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
                        imageData = applyXrayEffect(imageData);
                        
                        // Display X-ray on canvas
                        canvasXray.width = tempCanvas.width;
                        canvasXray.height = tempCanvas.height;
                        xrayCtx.putImageData(imageData, 0, 0);
                        
                        // Send frame for threat detection every 2 frames
                        frameCount++;
                        frameCountEl.textContent = frameCount;
                        
                        if (frameCount % 2 === 0) {
                            // Convert canvas to blob and send for detection
                            tempCanvas.toBlob(blob => {
                                uploadFrame(blob);
                            }, 'image/jpeg', 0.6);
                        }
                    }
                } catch (err) {
                    console.error('Frame capture error:', err);
                }
                
                requestAnimationFrame(captureFrames);
            }
            
            // Upload and detect threats in frame
            function uploadFrame(blob) {
                const formData = new FormData();
                formData.append('frame', blob);
                
                fetch('/detect_dual', { method: 'POST', body: formData })
                    .then(r => r.json())
                    .then(data => {
                        if (data.detections) {
                            updateDetections(data.detections);
                            if (data.detections.length > 0) {
                                addThreatLog(data.detections);
                            }
                        }
                    })
                    .catch(err => console.error('Detection error:', err));
            }
            
            // Upload Image File
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.style.background = 'rgba(0, 212, 255, 0.2)';
            });
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.style.background = '';
            });
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.style.background = '';
                if (e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files[0]) handleFileUpload(e.target.files[0]);
            });
            
            function handleFileUpload(file) {
                if (!file) return;
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/upload', { method: 'POST', body: formData })
                    .then(r => r.json())
                    .then(data => {
                        if (data.detections) {
                            updateDetections(data.detections);
                            if (data.detections.length > 0) {
                                addThreatLog(data.detections);
                            }
                        }
                    })
                    .catch(err => console.error('Upload error:', err));
            }
            
            function updateDetections(detections) {
                threatCountEl.textContent = detections.length;
                
                if (detections.length === 0) {
                    detectionsEl.innerHTML = '<p style="color: var(--text-muted); text-align: center; grid-column: 1/-1;">✓ Scan active - No threats yet</p>';
                    return;
                }
                
                let html = '';
                detections.forEach(d => {
                    const severity = (d.severity || 'INFO').toUpperCase();
                    const severityClass = severity === 'CRITICAL' ? 'critical' : severity === 'HIGH' ? 'warning' : '';
                    const confPercent = (d.confidence * 100).toFixed(0);
                    
                    html += `
                        <div class="detection-item ${severityClass}">
                            <div class="item-name">🚨 ${d.item}</div>
                            <div class="item-severity ${severity.toLowerCase()}">${severity}</div>
                            <div style="font-size: 0.8em; color: var(--text-muted); margin-top: 5px;">Confidence: ${confPercent}%</div>
                            ${d.bbox ? `<div style="font-size: 0.75em; color: #00ff00; margin-top: 3px;">📍 [${d.bbox[0]}, ${d.bbox[1]}]</div>` : ''}
                        </div>
                    `;
                });
                detectionsEl.innerHTML = html;
            }
            
            function addThreatLog(detections) {
                const timestamp = new Date().toLocaleTimeString();
                let logHtml = '';
                
                if (threatLogEl.querySelector('p')) {
                    threatLogEl.innerHTML = '';
                }
                
                detections.forEach(d => {
                    const severity = (d.severity || '').toUpperCase();
                    const severityClass = severity === 'CRITICAL' ? 'critical' : '';
                    logHtml += `
                        <div class="threat-entry">
                            <div class="threat-time">[${timestamp}]</div>
                            <strong class="threat-item ${severityClass}">🚨 ${d.item.toUpperCase()}</strong>
                            <div style="font-size: 0.85em; margin-top: 3px;">Severity: <strong>${d.severity || 'HIGH'}</strong> | Confidence: ${(d.confidence * 100).toFixed(0)}%</div>
                        </div>
                    `;
                });
                
                threatLogEl.insertAdjacentHTML('afterbegin', logHtml);
                
                // Keep only last 20 entries
                const entries = threatLogEl.querySelectorAll('.threat-entry');
                if (entries.length > 20) {
                    entries[entries.length - 1].remove();
                }
            }
            
            // Socket events
            socket.on('detection_update', (data) => {
                if (data.detections) {
                    updateDetections(data.detections);
                    addThreatLog(data.detections);
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_ROOT, filename)
    file.save(filepath)
    
    # Detect objects in uploaded image
    detections = detection_module.detect_threats(filepath)
    
    return jsonify({
        "success": True,
        "file": filename,
        "detections": detections
    })

@app.route("/detect", methods=["POST"])
def detect():
    if "frame" not in request.files:
        return jsonify({"error": "No frame provided"}), 400
    
    frame = request.files["frame"]
    frame_data = frame.read()
    
    # Convert byte stream to image
    img = Image.open(io.BytesIO(frame_data))
    
    # Temporary save for processing
    temp_path = os.path.join(UPLOAD_ROOT, "temp_frame.jpg")
    img.save(temp_path)
    
    # Detect objects
    result = detection_module.detect_threats(temp_path)
    
    # Handle both old and new return formats
    if isinstance(result, dict) and "detections" in result:
        detections = result["detections"]
    else:
        detections = result if isinstance(result, list) else []
    
    return jsonify({
        "success": True,
        "detections": detections
    })

@app.route("/detect_dual", methods=["POST"])
def detect_dual():
    """
    Real-time threat detection with YOLOv8.
    Used for continuous frame scanning with dual cameras.
    """
    if "frame" not in request.files:
        return jsonify({"error": "No frame provided"}), 400
    
    try:
        frame_file = request.files["frame"]
        frame_data = frame_file.read()
        
        # Convert byte stream to OpenCV format
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"detections": []})
        
        # Run real object detection
        result = detection_module.detect_threats_from_frame(frame, "stream")
        detections = result.get("detections", [])
        
        # Filter for only threats (not INFO level items unless suspicious context)
        threat_detections = [d for d in detections if d.get("severity") in ["CRITICAL", "HIGH", "SCANNING"]]
        
        return jsonify({
            "success": True,
            "detections": threat_detections
        })
    
    except Exception as e:
        print(f"Dual detection error: {e}")
        return jsonify({"success": False, "detections": [], "error": str(e)})

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)

# ---------------------------
# AI FRAUD DETECTION
# ---------------------------
def detect_fraud(project_id, new_data):
    history = payment_history.get(project_id, [])

    # Need minimum history for training
    if len(history) < 5:
        return False

    data = np.array(history)

    model = IsolationForest(contamination=0.15, random_state=42)
    model.fit(data)

    new_sample = np.array(new_data).reshape(1, -1)
    prediction = model.predict(new_sample)

    return prediction[0] == -1


# ---------------------------
# LOGIN
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    login_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login — Transparency Dashboard</title>
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
            :root{ --bg1:#0f172a; --bg2:#06202f; --accent:#7dd3fc; --accent-2:#7c3aed; --glass: rgba(255,255,255,0.04); }
            html,body{height:100%;}
            body { font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: radial-gradient(1200px 600px at 10% 10%, rgba(124,58,237,0.12), transparent), radial-gradient(900px 400px at 90% 90%, rgba(34,197,94,0.08), transparent), linear-gradient(180deg,var(--bg1),var(--bg2)); display:flex; align-items:center; justify-content:center; margin:0; }
            .scene { width:100%; max-width:980px; padding:28px; box-sizing:border-box; }
            .card { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius:16px; padding:28px; box-shadow: 0 10px 30px rgba(2,6,23,0.6), inset 0 1px 0 rgba(255,255,255,0.02); display:flex; gap:20px; align-items:center; }
            .left { flex:1; color: #e6f6ff; }
            .brand { font-weight:800; font-size:20px; margin-bottom:6px; }
            .subtitle { color:rgba(230,246,255,0.8); margin-bottom:18px; }
            .roles { display:flex; gap:10px; margin-bottom:16px; }
            .role-btn { flex:1; padding:10px 12px; border-radius:10px; border:1px solid transparent; cursor:pointer; background:transparent; color:rgba(230,246,255,0.9); transition: all 220ms ease; position:relative; overflow:hidden; }
            .role-btn::after { content:''; position:absolute; inset:0; border-radius:10px; box-shadow: 0 0 18px rgba(125,211,252,0); transition:box-shadow 220ms ease; }
            .role-btn:hover::after { box-shadow: 0 6px 28px rgba(125,211,252,0.06); }
            .role-btn.active { background: linear-gradient(90deg, rgba(125,211,252,0.08), rgba(124,58,237,0.06)); border:1px solid rgba(125,211,252,0.18); }
            .role-btn.active::after { box-shadow: 0 6px 30px rgba(125,211,252,0.18); }
            .hint { font-size:13px; color:rgba(230,246,255,0.8); margin-bottom:8px; }
            .right { width:360px; }
            form { display:flex; flex-direction:column; gap:12px; }
            label { font-size:13px; color:rgba(200,220,240,0.9); }
            .field { position:relative; }
            input[type="text"], input[type="password"] { width:100%; padding:12px 14px; border-radius:10px; border:1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); color: #e6f6ff; outline:none; transition: box-shadow 180ms ease, border-color 180ms ease, transform 180ms ease; }
            input::placeholder{ color: rgba(230,246,255,0.35); }
            input:focus { box-shadow: 0 6px 30px rgba(124,58,237,0.12); border-color: rgba(125,211,252,0.22); transform: translateY(-2px); }
            .submit { width:100%; padding:12px; border-radius:12px; background: linear-gradient(90deg,var(--accent),var(--accent-2)); color:#021124; border:0; font-weight:700; cursor:pointer; box-shadow: 0 8px 30px rgba(124,58,237,0.16); transition: transform 160ms ease, box-shadow 160ms ease; }
            .submit:hover { transform: translateY(-3px); box-shadow: 0 14px 40px rgba(124,58,237,0.22); }
            .glow { position:absolute; inset:-2px; border-radius:14px; pointer-events:none; background: linear-gradient(90deg, rgba(125,211,252,0.06), rgba(124,58,237,0.06)); filter: blur(14px); opacity:0; transition: opacity 220ms ease; }
            .submit:active + .glow, .submit:focus + .glow { opacity:1; }
            .error { color:#ffb4b4; background:rgba(255,20,60,0.04); padding:8px 10px; border-radius:8px; }
            .small { font-size:12px; color:rgba(230,246,255,0.7); margin-top:8px; text-align:center; }
            .demo-note { font-size:12px; color:rgba(230,246,255,0.6); text-align:center; margin-top:6px; }
            @media (max-width:820px) { .card{flex-direction:column;padding:18px;} .right{width:100%} }
        </style>
    </head>
    <body>
        <div class="scene">
            <div class="card" role="main">
                <div class="left">
                    <div class="brand">Transparency Dashboard</div>
                    <div class="subtitle">Secure access to the public funds transparency system</div>

                    {% if error %}
                        <div class="error">{{error}}</div>
                    {% endif %}

                    <div class="roles" role="tablist" aria-label="Select role">
                        <button type="button" id="govBtn" class="role-btn" onclick="selectRole('government','gov','gov123')">Government</button>
                        <button type="button" id="contractorBtn" class="role-btn" onclick="selectRole('contractor','contractor','contract123')">Contractor</button>
                        <button type="button" id="publicBtn" class="role-btn" onclick="selectRole('public','public','public123')">Public</button>
                    </div>

                    <div class="hint" id="roleHint">Select a role to auto-fill demo credentials.</div>
                    <div class="demo-note">Demo accounts: gov / gov123 • contractor / contract123 • public / public123</div>
                </div>

                <div class="right">
                    <form method="POST" onsubmit="return ensureRoleSelected();">
                        <input type="hidden" name="role" id="roleInput" value="{{selected_role}}">
                        <div class="field">
                            <label for="username">Username</label>
                            <input id="username" type="text" name="username" placeholder="Enter username" autocomplete="username" value="">
                        </div>

                        <div class="field">
                            <label for="password">Password</label>
                            <input id="password" type="password" name="password" placeholder="Enter password" autocomplete="current-password" value="">
                        </div>

                        <div style="position:relative">
                            <button class="submit" type="submit">Sign in</button>
                            <div class="glow"></div>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <script>
            const roleMap = {
                "government": {user: "gov", pass: "gov123", btnId: "govBtn"},
                "contractor": {user: "contractor", pass: "contract123", btnId: "contractorBtn"},
                "public": {user: "public", pass: "public123", btnId: "publicBtn"}
            };

            function clearActive() {
                Object.values(roleMap).forEach(r => document.getElementById(r.btnId).classList.remove('active'));
            }

            function selectRole(role, username, passwordHint) {
                document.getElementById('roleInput').value = role;
                document.getElementById('username').value = username;
                document.getElementById('password').value = passwordHint;
                document.getElementById('roleHint').innerText = 'Selected role: ' + role + ' — demo credentials auto-filled.';
                clearActive();
                const btn = document.getElementById(roleMap[role].btnId);
                if (btn) btn.classList.add('active');
                // subtle scale effect
                btn.animate([{ transform: 'scale(0.98)' }, { transform: 'scale(1)' }], { duration: 180, easing: 'ease-out' });
            }

            function ensureRoleSelected() {
                const role = document.getElementById('roleInput').value;
                if (!role) {
                    // friendly inline hint instead of alert
                    const hint = document.getElementById('roleHint');
                    hint.style.color = '#ffb4b4';
                    hint.innerText = 'Please select a role before logging in.';
                    setTimeout(()=>{ hint.style.color=''; hint.innerText='Select a role to auto-fill demo credentials.'; }, 2500);
                    return false;
                }
                return true;
            }

            // If server passed a selected_role, mark it active on load
            (function init() {
                const sel = "{{selected_role}}";
                if (sel && roleMap[sel]) selectRole(sel, roleMap[sel].user, roleMap[sel].pass);
            })();
        </script>
    </body>
    </html>
    """

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "")

        if username in users and users[username]["password"] == password and users[username]["role"] == selected_role:
            session["role"] = users[username]["role"]
            return redirect("/")
        else:
            error = "Invalid credentials or role. Make sure role matches the account."
            return render_template_string(login_html, error=error, selected_role=selected_role)

    return render_template_string(login_html, error=None, selected_role="")


@app.route("/logout")
def logout():
    session.pop("role", None)
    return redirect("/login")

# ---------------------------
# CREATE PROJECT (Government Only)
# ---------------------------
@app.route("/create_project", methods=["GET", "POST"])
def create_project():
    if session.get("role") != "government":
        return "Unauthorized"

    if request.method == "POST":
        project_id = request.form["project_id"]
        name = request.form["name"]
        budget = float(request.form["budget"])
        contractor_name = request.form["contractor"]

        project = GovernmentProject(project_id, name, budget)
        contractor = Contractor(project_id, contractor_name)

        projects[project_id] = project
        contractors[project_id] = contractor
        payment_history[project_id] = []
        work_logs[project_id] = []
        ratings[project_id] = []
 
        blockchain.add_block({
            "action": "Project Created",
            "project_id": project_id,
            "name": name,
            "budget": budget,
            "contractor": contractor_name
        })

        # notify connected clients about the new project
        try:
            socketio.emit('refresh', {'msg': f'Project {project_id} created'}, broadcast=True)
        except Exception:
            pass

        return redirect("/")

    return """
        <h2>Create New Project</h2>
        <form method="POST">
            Project ID: <input name="project_id"><br><br>
            Project Name: <input name="name"><br><br>
            Budget: <input name="budget"><br><br>
            Contractor Name: <input name="contractor"><br><br>
            <button type="submit">Create</button>
        </form>
    """

# ---------------------------
# RELEASE FUNDS
# ---------------------------
@app.route("/release/<project_id>")
def release(project_id):
    if session.get("role") != "government":
        return "Unauthorized"

    project = projects.get(project_id)
    contractor = contractors.get(project_id)

    if not project:
        return "Project not found"

    for milestone in project.milestones:
        if milestone not in project.completed_milestones:
            amount = project.release_funds(milestone)

            if isinstance(amount, float):
                contractor.receive_funds(amount)

                blockchain.add_block({
                    "action": "Milestone Completed",
                    "project_id": project_id,
                    "milestone": milestone,
                    "released_amount": amount,
                    "contractor_balance": contractor.balance
                })
                # notify clients about milestone release
                try:
                    socketio.emit('refresh', {'msg': f'Milestone {milestone} released for {project_id}'}, broadcast=True)
                except Exception:
                    pass
                # record a simple work log (days_taken placeholder or computed)
                completed_at = datetime.datetime.utcnow().isoformat()
                # simple heuristic: days_taken = 7
                days_taken = 7
                work_logs.setdefault(project_id, []).append({
                    "milestone": milestone,
                    "completed_at": completed_at,
                    "days_taken": days_taken
                })

            break
    else:
        return "All milestones already completed."

    return redirect("/")


# ---------------------------
# CONTRACTOR PAYMENT WITH AI FRAUD CHECK
# ---------------------------
@app.route("/pay/<project_id>", methods=["GET", "POST"])
def pay(project_id):
    if session.get("role") != "contractor":
        return "Unauthorized"

    contractor = contractors.get(project_id)
    project = projects.get(project_id)

    if not contractor:
        return "Invalid Project"
    if request.method == "POST":
        # Expect files: before and after images, plus recipient and amount
        recipient = request.form.get("recipient", "").strip()
        try:
            amount = float(request.form.get("amount", 0))
        except:
            return "Invalid amount"

        before_file = request.files.get("before")
        after_file = request.files.get("after")

        if not before_file or not allowed_file(before_file.filename):
            return "Invalid or missing BEFORE image."
        if not after_file or not allowed_file(after_file.filename):
            return "Invalid or missing AFTER image."

        # save files under uploads/<project_id>/
        proj_dir = os.path.join(UPLOAD_ROOT, project_id)
        os.makedirs(proj_dir, exist_ok=True)

        before_fn = secure_filename(f"pay_before_{int(__import__('time').time())}_{before_file.filename}")
        after_fn = secure_filename(f"pay_after_{int(__import__('time').time())}_{after_file.filename}")

        before_path = os.path.join(proj_dir, before_fn)
        after_path = os.path.join(proj_dir, after_fn)
        before_file.save(before_path)
        after_file.save(after_path)

        # Verify images using AI helper
        try:
            res = image_module.verify_progress(before_path, after_path)
        except Exception as e:
            return f"Image verification failed: {e}"

        if not res.get("verdict"):
            # record attempt on blockchain for audit
            blockchain.add_block({
                "action": "Payment Image Verification Failed",
                "project_id": project_id,
                "details": res
            })
            try:
                socketio.emit('refresh', {'msg': f'Payment image verification failed for {project_id}'}, broadcast=True)
            except Exception:
                pass
            return f"Payment blocked by image verification. Score={res.get('score'):.4f} (threshold={res.get('threshold')})"

        # Passed image check → continue existing fraud check + payment
        feature_data = [
            amount,
            contractor.balance,
            amount / project.total_budget if project and project.total_budget else 0
        ]

        if detect_fraud(project_id, feature_data):
            blockchain.add_block({
                "action": "⚠️ Fraud Attempt Blocked",
                "project_id": project_id,
                "attempted_amount": amount,
                "recipient": recipient
            })
            try:
                socketio.emit('refresh', {'msg': f'Fraud attempt blocked for {project_id}'}, broadcast=True)
            except Exception:
                pass
            return "🚨 Fraud Detected! Payment Blocked by AI."

        # Make payment
        payment = contractor.make_payment(recipient, amount)
        if isinstance(payment, dict):
            payment_history.setdefault(project_id, []).append(feature_data)
            blockchain.add_block({
                "action": "Contractor Payment",
                "project_id": project_id,
                "details": payment,
                "remaining_balance": contractor.balance,
                "images": {"before": before_fn, "after": after_fn}
            })
            try:
                socketio.emit('refresh', {'msg': f'Payment made for {project_id}'}, broadcast=True)
            except Exception:
                pass

        return redirect("/")

    # GET → show upload form for before/after
    return f"""
        <div style="min-height:70vh;display:flex;align-items:center;justify-content:center;padding:28px;background:linear-gradient(180deg,#071427,#031021);">
            <div style="width:100%;max-width:720px;background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01));border-radius:14px;padding:22px;box-shadow:0 12px 40px rgba(2,6,23,0.7);color:#e6f6ff;font-family:Inter, system-ui, -apple-system, Arial;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
                    <h2 style="margin:0;font-size:18px;">Make Payment — <span style="color:#7dd3fc">{project_id}</span></h2>
                    <div style="font-size:12px;color:rgba(230,246,255,0.75)">Secure upload • AI verification</div>
                </div>

                <form method="POST" enctype="multipart/form-data" style="display:flex;flex-direction:column;gap:12px;">
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <div style="flex:1;min-width:220px;">
                            <label style="font-size:13px;color:rgba(230,246,255,0.85);font-weight:700">Recipient</label><br>
                            <input name="recipient" placeholder="Recipient name or account" style="width:100%;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:#e6f6ff;">
                        </div>

                        <div style="width:160px;min-width:140px;">
                            <label style="font-size:13px;color:rgba(230,246,255,0.85);font-weight:700">Amount (₹)</label><br>
                            <input name="amount" type="number" step="0.01" placeholder="0.00" style="width:100%;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:#e6f6ff;text-align:right;">
                        </div>
                    </div>

                    <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap;">
                        <div style="flex:1;min-width:260px;">
                            <label style="font-size:13px;color:rgba(230,246,255,0.85);font-weight:700">Before image (current state)</label><br>
                            <input type="file" name="before" accept="image/*" required onchange="document.getElementById('beforePreview').src=window.URL.createObjectURL(this.files[0])" style="margin-top:6px;">
                        </div>

                        <div style="flex:1;min-width:260px;">
                            <label style="font-size:13px;color:rgba(230,246,255,0.85);font-weight:700">After image (work done)</label><br>
                            <input type="file" name="after" accept="image/*" required onchange="document.getElementById('afterPreview').src=window.URL.createObjectURL(this.files[0])" style="margin-top:6px;">
                        </div>

                        <div style="width:140px;display:flex;flex-direction:column;gap:8px;align-items:center;">
                            <div style="font-size:12px;color:rgba(230,246,255,0.75)">Preview</div>
                            <img id="beforePreview" src="" alt="before" style="width:120px;height:80px;object-fit:cover;border-radius:8px;background:linear-gradient(180deg,rgba(255,255,255,0.01),rgba(255,255,255,0.005));">
                            <img id="afterPreview" src="" alt="after" style="width:120px;height:80px;object-fit:cover;border-radius:8px;background:linear-gradient(180deg,rgba(255,255,255,0.01),rgba(255,255,255,0.005));">
                        </div>
                    </div>

                    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:6px;">
                        <div style="font-size:12px;color:rgba(230,246,255,0.75)">Allowed: png, jpg, jpeg, gif</div>
                        <div>
                            <button type="submit" style="padding:12px 16px;border-radius:12px;border:0;box-shadow:0 10px 30px rgba(124,58,237,0.12);background:linear-gradient(90deg,#7dd3fc,#7c3aed);color:#021124;font-weight:800;cursor:pointer;transition:transform .16s ease;" onmouseover="this.style.transform='translateY(-3px)'" onmouseout="this.style.transform=''">Submit Payment</button>
                        </div>
                    </div>
                </form>

            </div>
        </div>
    """


# New route: contractor uploads before/after images and requests next phase funding
@app.route("/request_phase/<project_id>", methods=["GET", "POST"])
def request_phase(project_id):
    if session.get("role") != "contractor":
        return "Unauthorized"

    project = projects.get(project_id)
    if not project:
        return "Invalid Project"

    if request.method == "POST":
        before = request.files.get("before")
        after = request.files.get("after")

        if not before or not allowed_file(before.filename):
            return "Invalid or missing BEFORE image."
        if not after or not allowed_file(after.filename):
            return "Invalid or missing AFTER image."

        # save files under uploads/<project_id>/
        proj_dir = os.path.join(UPLOAD_ROOT, project_id)
        os.makedirs(proj_dir, exist_ok=True)

        before_fn = secure_filename(f"before_{int(__import__('time').time())}_{before.filename}")
        after_fn = secure_filename(f"after_{int(__import__('time').time())}_{after.filename}")

        before.save(os.path.join(proj_dir, before_fn))
        after.save(os.path.join(proj_dir, after_fn))

        funding_requests[project_id] = {
            "status": "pending",
            "before": before_fn,
            "after": after_fn,
            "requested_by": "contractor"  # demo: username or session-based id
        }

        # record request on blockchain
        blockchain.add_block({
            "action": "Funding Requested",
            "project_id": project_id,
            "requested_by": funding_requests[project_id]["requested_by"]
        })
        try:
            socketio.emit('refresh', {'msg': f'Funding requested for {project_id}'}, broadcast=True)
        except Exception:
            pass

        return redirect("/")

    # GET → show simple upload form
    return f"""
        <h2>Request Next Phase Funding — Project {project_id}</h2>
        <form method="POST" enctype="multipart/form-data">
            Before Image: <input type="file" name="before" accept="image/*" required><br><br>
            After Image: <input type="file" name="after" accept="image/*" required><br><br>
            <button type="submit">Submit Funding Request</button>
        </form>
    """

# New route: government approve/deny a funding request
@app.route("/approve_request/<project_id>", methods=["POST"])
def approve_request(project_id):
    if session.get("role") != "government":
        return "Unauthorized"

    req = funding_requests.get(project_id)
    if not req or req.get("status") != "pending":
        return "No pending request."

    decision = request.form.get("decision")
    if decision == "approve":
        # approve: release next milestone for the project
        # reuse release logic by calling release() route handler function directly
        funding_requests[project_id]["status"] = "approved"
        blockchain.add_block({
            "action": "Funding Approved",
            "project_id": project_id,
            "approved_by": "government"
        })
        try:
            socketio.emit('refresh', {'msg': f'Funding approved for {project_id}'}, broadcast=True)
        except Exception:
            pass
        # call release to actually release funds (it will add its own block)
        return release(project_id)
    else:
        funding_requests[project_id]["status"] = "denied"
        blockchain.add_block({
            "action": "Funding Denied",
            "project_id": project_id,
            "denied_by": "government"
        })
        try:
            socketio.emit('refresh', {'msg': f'Funding denied for {project_id}'}, broadcast=True)
        except Exception:
            pass
        return redirect("/")

# New route: contractor requests top-up funds
@app.route("/request_topup/<project_id>", methods=["GET", "POST"])
def request_topup(project_id):
    if session.get("role") != "contractor":
        return "Unauthorized"
    project = projects.get(project_id)
    if not project:
        return "Invalid Project"

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
        except:
            return "Invalid amount"

        message = request.form.get("message", "").strip()
        req_id = str(int(__import__('time').time()*1000))
        req = {
            "id": req_id,
            "amount": amount,
            "message": message,
            "status": "pending",
            "requested_by": "contractor",
            "ts": req_id
        }
        fund_requests.setdefault(project_id, []).append(req)

        blockchain.add_block({
            "action": "Topup Requested",
            "project_id": project_id,
            "amount": amount,
            "requested_by": req["requested_by"]
        })
        try:
            socketio.emit('refresh', {'msg': f'Topup requested for {project_id}'}, broadcast=True)
        except Exception:
            pass

        return redirect("/")

    return f"""
        <h2>Request Additional Funds — Project {project_id}</h2>
        <form method="POST">
            Amount: <input name="amount" type="number" step="0.01" required><br><br>
            Message: <input name="message"><br><br>
            <button type="submit">Request Funds</button>
        </form>
    """

# New route: government approves/denies top-up
@app.route("/handle_topup/<project_id>/<req_id>", methods=["POST"])
def handle_topup(project_id, req_id):
    if session.get("role") != "government":
        return "Unauthorized"
    lst = fund_requests.get(project_id, [])
    req = next((r for r in lst if r["id"] == req_id), None)
    if not req or req["status"] != "pending":
        return "No pending request"
    decision = request.form.get("decision")
    if decision == "approve":
        req["status"] = "approved"
        blockchain.add_block({
            "action": "Topup Approved",
            "project_id": project_id,
            "amount": req["amount"],
            "approved_by": "government"
        })
        try:
            socketio.emit('refresh', {'msg': f'Topup approved for {project_id}'}, broadcast=True)
        except Exception:
            pass
        # release next milestone (same behavior as release route)
        return release(project_id)
    else:
        req["status"] = "denied"
        blockchain.add_block({
            "action": "Topup Denied",
            "project_id": project_id,
            "denied_by": "government"
        })
        try:
            socketio.emit('refresh', {'msg': f'Topup denied for {project_id}'}, broadcast=True)
        except Exception:
            pass
        return redirect("/")

# Serve uploaded images
@app.route("/uploads/<project_id>/<filename>")
def uploaded_file(project_id, filename):
    proj_dir = os.path.join(UPLOAD_ROOT, project_id)
    return send_from_directory(proj_dir, filename)

# ---------------------------
# HOME DASHBOARD
# ---------------------------
@app.route("/")
def home():
    if "role" not in session:
        return redirect("/login")

    role = session["role"]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Transparency Dashboard</title>
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
            :root{ --bg-a:#071033; --bg-b:#081222; --card:#071427; --glass: rgba(255,255,255,0.03); --accent-1: #60a5fa; --accent-2:#7dd3fc; --accent-3:#a78bfa; }
            *{box-sizing:border-box}
            body{margin:0;font-family:'Inter', 'Segoe UI', system-ui, -apple-system, Arial; background: linear-gradient(135deg,var(--bg-a), var(--bg-b)); color:#e6f6ff; -webkit-font-smoothing:antialiased;}
            header{padding:24px;text-align:center;background:linear-gradient(180deg, rgba(255,255,255,0.02), transparent);backdrop-filter: blur(6px);}
            header h1{margin:0;font-size:20px;letter-spacing:0.2px}
            header p{margin:6px 0 0 0;color:rgba(230,246,255,0.78)}
            .container{padding:28px;max-width:1200px;margin:0 auto}
            .card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));border-radius:14px;padding:18px;margin-bottom:18px;box-shadow: 0 8px 30px rgba(2,6,23,0.6);transition: transform 220ms ease, box-shadow 220ms ease}
            .card:hover{transform: translateY(-6px);box-shadow: 0 20px 50px rgba(2,6,23,0.7)}
            .btn{padding:10px 14px;border-radius:10px;font-weight:700;text-decoration:none;display:inline-block;border:0;cursor:pointer}
            .btn-blue{background:linear-gradient(90deg,var(--accent-1),var(--accent-3));color:#021124;box-shadow:0 10px 30px rgba(99,102,241,0.12)}
            .btn-green{background:linear-gradient(90deg,#34d399,#60a5fa);color:#021124}
            .btn-red{background:linear-gradient(90deg,#fb7185,#ef4444);color:#021124}
            .btn:active{transform: translateY(1px)}
            .analysis-grid{display:flex;gap:14px;flex-wrap:wrap}
            .chart-card{background:linear-gradient(180deg, rgba(255,255,255,0.015), rgba(255,255,255,0.01));padding:14px;border-radius:12px;flex:1;min-width:260px}
            .stat-row{display:flex;gap:10px;margin-bottom:10px}
            .stat{flex:1;background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.005));padding:10px;border-radius:10px;text-align:center}
            .stat strong{display:block;font-size:18px;color:#fff}
            .ledger-header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}
            .ledger-search{padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:rgba(230,246,255,0.9);min-width:220px}
            .ledger-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin-top:8px}
            .ledger-card{padding:14px;border-radius:12px;background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));box-shadow:0 6px 18px rgba(2,6,23,0.5);transition:transform 180ms ease, box-shadow 180ms ease}
            .ledger-card:hover{transform:translateY(-8px);box-shadow:0 24px 44px rgba(2,6,23,0.68)}
            .action-badge{padding:6px 8px;border-radius:8px;font-size:12px;font-weight:700;color:#071133}
            .badge-created{background:#fef3c7}
            .badge-milestone{background:#bbf7d0}
            .badge-payment{background:#bfdbfe}
            .ledger-meta{display:flex;justify-content:space-between;margin-top:12px;font-size:12px;color:rgba(230,246,255,0.75)}
            .hash{font-family:monospace;font-size:12px;color:#dbeafe}
            .copy-btn{background:transparent;border:1px solid rgba(255,255,255,0.06);color:#fff;padding:6px 8px;border-radius:8px;cursor:pointer}
            .projects-list{display:grid;gap:12px}
            @media(min-width:900px){.projects-list{grid-template-columns:repeat(2,1fr)}}
            .project-compact{display:flex;gap:16px;align-items:center;justify-content:space-between;padding:14px;border-radius:12px;background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.005));box-shadow:0 8px 26px rgba(2,6,23,0.45);position:relative;overflow:hidden}
            .project-compact::after{content:'';position:absolute;right:-60px;top:-60px;width:200px;height:200px;background:radial-gradient(circle at 30% 30%, rgba(125,211,252,0.06), transparent 30%), radial-gradient(circle at 70% 70%, rgba(167,139,250,0.04), transparent 30%);transform:rotate(15deg);pointer-events:none}
            .project-info{flex:1;min-width:0}
            .project-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 0 6px 0;font-weight:700;font-size:15px}
            .project-meta{color:rgba(230,246,255,0.78);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}
            .progress{background:rgba(255,255,255,0.03);border-radius:10px;overflow:hidden;height:12px;margin-top:10px}
            .progress-bar{height:100%;background:linear-gradient(90deg,#34d399,#60a5fa);width:0%;transition:width 900ms cubic-bezier(.2,.8,.2,1)}
            .project-actions{display:flex;flex-direction:column;gap:8px;align-items:flex-end;min-width:140px;z-index:2;position:relative}
            .muted{color:rgba(230,246,255,0.7);font-size:12px}
            .small-btn{padding:8px 10px;border-radius:10px;font-size:13px;text-decoration:none;color:#021124}
            .small-btn.green{background:linear-gradient(90deg,#6ee7b7,#60a5fa)}
            .small-btn.blue{background:linear-gradient(90deg,#60a5fa,#7c3aed);color:#fff}
            .project-badge{background:rgba(255,255,255,0.04);padding:6px 8px;border-radius:8px;font-weight:700;font-size:12px;color:#fff}
            .transactions{display:none}
            .transactions.show{display:block}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <script>
            const socket = io();
            socket.on('refresh', function(data){
                try{ toast('Update: '+(data.msg||'')); }catch(e){}
                // reload shortly so UI reflects the latest state
                setTimeout(function(){ location.reload(); }, 900);
            });
        </script>
    </head>
    <body>
        <header>
            <h1>🚀 National Public Fund Transparency System</h1>
            <p>Logged in as: <strong>{{role}}</strong></p>
            <a href="/logout" class="btn btn-red">Logout</a>
        </header>
        <div class="container">
    <!-- header and container start -->

        {% if role == "government" %}
            <div class="card" style="display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap;">
                <div style="flex:1;min-width:320px;">
                    <h2>🏛 Government Controls</h2>
                    <form method="POST" action="/create_project" style="display:flex;flex-direction:column;gap:8px;max-width:480px;">
                        <input name="project_id" placeholder="Project ID" style="padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:transparent;color:white;">
                        <input name="name" placeholder="Project Name" style="padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:transparent;color:white;">
                        <input name="budget" placeholder="Budget" type="number" step="0.01" style="padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:transparent;color:white;">
                        <select name="contractor" style="padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:transparent;color:white;">
                            {% for c in available_contractors %}
                                <option value="{{c}}">{{c}}</option>
                            {% endfor %}
                        </select>
                        <button type="submit" class="btn btn-blue" style="width:160px;">Create Project</button>
                    </form>

                    <!-- Show pending funding requests to Government -->
                    <div style="margin-top:14px;">
                        <h3 style="margin:6px 0 8px 0;">🔎 Pending Funding Requests</h3>
                        {% for pid, req in funding_requests.items() %}
                            {% if req.status == 'pending' %}
                                <div style="background:rgba(0,0,0,0.16);padding:10px;border-radius:10px;margin-bottom:10px;">
                                    <div style="display:flex;justify-content:space-between;align-items:center;">
                                        <div><strong>{{pid}}</strong> &nbsp; <span style="color:rgba(255,255,255,0.75)">requested by {{req.requested_by}}</span></div>
                                        <div>
                                            <form method="POST" action="/approve_request/{{pid}}" style="display:inline;">
                                                <button class="btn btn-green" name="decision" value="approve">Approve</button>
                                            </form>
                                            <form method="POST" action="/approve_request/{{pid}}" style="display:inline;">
                                                <button class="btn btn-red" name="decision" value="deny">Deny</button>
                                            </form>
                                        </div>
                                    </div>
                                    <div style="display:flex;gap:8px;margin-top:8px;">
                                        <a href="/uploads/{{pid}}/{{req.before}}" target="_blank"><img src="/uploads/{{pid}}/{{req.before}}" style="width:140px;height:90px;object-fit:cover;border-radius:6px;"></a>
                                        <a href="/uploads/{{pid}}/{{req.after}}" target="_blank"><img src="/uploads/{{pid}}/{{req.after}}" style="width:140px;height:90px;object-fit:cover;border-radius:6px;"></a>
                                    </div>
                                </div>
                            {% endif %}
                        {% endfor %}

                        <!-- Show pending top-up requests -->
                        <h3 style="margin:6px 0 8px 0;">💰 Pending Top-up Requests</h3>
                        {% for pid, reqs in fund_requests.items() %}
                            {% for req in reqs %}
                                {% if req.status == 'pending' %}
                                    <div style="background:rgba(0,0,0,0.16);padding:10px;border-radius:10px;margin-bottom:10px;">
                                        <div style="display:flex;justify-content:space-between;align-items:center;">
                                            <div><strong>{{pid}}</strong> &nbsp; <span style="color:rgba(255,255,255,0.75)">requested by {{req.requested_by}}</span></div>
                                            <div>
                                                <form method="POST" action="/handle_topup/{{pid}}/{{req.id}}" style="display:inline;">
                                                    <button class="btn btn-green" name="decision" value="approve">Approve</button>
                                                </form>
                                                <form method="POST" action="/handle_topup/{{pid}}/{{req.id}}" style="display:inline;">
                                                    <button class="btn btn-red" name="decision" value="deny">Deny</button>
                                                </form>
                                            </div>
                                        </div>
                                        <div style="margin-top:8px;">
                                            <strong>Amount:</strong> ₹{{req.amount}} <br>
                                            <strong>Message:</strong> {{req.message}}
                                        </div>
                                    </div>
                                {% endif %}
                            {% endfor %}
                        {% endfor %}
                    </div>
                </div>

                <div style="width:320px;">
                    <div class="analysis-grid">
                        <div class="chart-card">
                            <h4 style="margin:4px 0 8px 0;">📊 Project Analysis</h4>
                            <div class="stat-row">
                                <div class="stat"><div style="font-size:12px;color:rgba(255,255,255,0.7)">Total</div><strong>{{project_stats.total_projects}}</strong></div>
                                <div class="stat"><div style="font-size:12px;color:rgba(255,255,255,0.7)">Active</div><strong>{{project_stats.active_projects}}</strong></div>
                                <div class="stat"><div style="font-size:12px;color:rgba(255,255,255,0.7)">Completed</div><strong>{{project_stats.completed_projects}}</strong></div>
                            </div>
                            <canvas id="statusChart" width="300" height="180"></canvas>
                        </div>

                        <div class="chart-card">
                            <h4 style="margin:4px 0 8px 0;">💰 Budget Overview</h4>
                            <div class="stat-row" style="margin-bottom:10px;">
                                <div class="stat"><div style="font-size:12px;color:rgba(255,255,255,0.7)">Total Budget</div><strong>₹{{project_stats.total_budget}}</strong></div>
                                <div class="stat"><div style="font-size:12px;color:rgba(255,255,255,0.7)">Released</div><strong>₹{{project_stats.total_released}}</strong></div>
                            </div>
                            <canvas id="budgetChart" width="300" height="180"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        {% endif %}

        <h2>📂 Active Projects</h2>

        {% if role == "public" %}
            <div class="projects-list">
                {% for pid, proj in projects.items() %}
                    <div class="project-compact project-card" onclick="openPublicModal('{{pid}}')">
                        <div class="project-info">
                            <div class="project-title">
                                <div style="display:flex;gap:8px;align-items:center;">
                                    <span style="font-size:14px;color:rgba(255,255,255,0.95)">{{proj.project_name}}</span>
                                    <span class="project-badge">{{pid}}</span>
                                </div>
                                <div class="muted">Contractor: {{ (contractors.get(pid).name) if contractors.get(pid) else '—' }}</div>
                            </div>
                            <div class="project-meta">
                                <div><strong>Total:</strong> ₹{{proj.total_budget}}</div>
                                <div><strong>Released:</strong> ₹{{proj.released_amount}}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Hidden details template for modal -->
                    <div id="details-{{pid}}" style="display:none;">
                        <h3>{{proj.project_name}} <small style="color:rgba(255,255,255,0.7)">{{pid}}</small></h3>
                        <p><strong>Contractor:</strong> {{ (contractors.get(pid).name) if contractors.get(pid) else '—' }}</p>
                        <p><strong>Work Done (completed milestones):</strong></p>
                        <ul>
                            {% for wl in work_logs.get(pid, []) %}
                                <li>{{ wl['milestone'] }} — completed at {{ wl['completed_at'] }} ({{ wl['days_taken'] }} days)</li>
                            {% endfor %}
                            {% if (work_logs.get(pid, []) | length) == 0 %}
                                <li>No completed work yet.</li>
                            {% endif %}
                        </ul>
                        <p><strong>Average Rating:</strong>
                            {% set rs = ratings.get(pid, []) %}
                            {% if rs and (rs|length) > 0 %}
                                {% set total = 0 %}
                                {% for r in rs %}
                                    {% set total = total + r['score'] %}
                                {% endfor %}
                                {{ (total / (rs|length)) | round(2) }} / 5 ({{ rs|length }} ratings)
                            {% else %}
                                No ratings yet.
                            {% endif %}
                        </p>
                        <hr>
                        <form method="POST" action="/rate/{{pid}}">
                            <label>Rate Contractor (1-5):</label><br>
                            <input type="number" name="score" min="1" max="5" required><br><br>
                            <label>Comment:</label><br>
                            <input type="text" name="comment" style="width:100%"><br><br>
                            <button type="submit" class="btn btn-blue">Submit Rating</button>
                        </form>
                    </div>
                {% endfor %}
            </div>
            <!-- modal -->
            <div id="publicModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); align-items:center; justify-content:center; z-index:2000;">
                <div id="publicModalContent" style="max-width:720px; width:90%; background:linear-gradient(180deg,#0b1220,#071033); padding:18px; border-radius:12px; color:white; overflow:auto; max-height:80vh;">
                    <button onclick="closeModal()" style="float:right;" class="btn btn-red">Close</button>
                    <div id="publicModalBody"></div>
                </div>
            </div>
            <script>
                function openPublicModal(pid){
                    const tpl = document.getElementById('details-' + pid);
                    if(!tpl) return;
                    document.getElementById('publicModalBody').innerHTML = tpl.innerHTML;
                    document.getElementById('publicModal').style.display = 'flex';
                }
                function closeModal(){
                    document.getElementById('publicModal').style.display = 'none';
                }
            </script>
        {% else %}
            <div class="projects-list">
                {% for pid, proj in projects.items() %}
                    {# compute release percentage safely #}
                    {% set pct = (proj.released_amount / proj.total_budget * 100) if proj.total_budget else 0 %}
                    <div class="project-compact project-card" data-pid="{{pid}}">
                        <div class="project-info">
                            <div class="project-title">
                                <div style="display:flex;gap:8px;align-items:center;">
                                    <span style="font-size:14px;color:rgba(255,255,255,0.9)">{{proj.project_name}}</span>
                                    <span class="project-badge">{{pid}}</span>
                            </div>
                            <div class="muted">Contractor: {{ (contractors.get(pid).name) if contractors.get(pid) else '—' }}</div>
                        </div>

                        <div class="project-meta">
                            <div><strong>Total:</strong> ₹{{proj.total_budget}}</div>
                            <div><strong>Released:</strong> ₹{{proj.released_amount}}</div>
                            <div><strong>Milestones:</strong> {{proj.completed_milestones|length}} / {{proj.milestones|length}}</div>
                        </div>

                        <div class="progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{{pct}}">
                            <div class="progress-bar" style="width: {{pct}}%;"></div>
                        </div>
                        <div class="muted" style="margin-top:6px;">Released: {{pct|round(1)}}%</div>
                    </div>

                    <div class="project-actions">
                        {% if role == "government" %}
                            <a href="/release/{{pid}}" class="small-btn green">Release Milestone</a>
                        {% endif %}
                        {% if role == "contractor" %}
                            <a href="/pay/{{pid}}" class="small-btn blue">Make Payment</a>
                            <a href="/request_topup/{{pid}}" class="small-btn green">Request Funds</a>
                        {% endif %}
                        <button class="small-btn" onclick="document.getElementById('tx-{{pid}}').classList.toggle('show'); document.getElementById('tx-{{pid}}').setAttribute('aria-hidden', document.getElementById('tx-{{pid}}').classList.contains('show') ? 'false' : 'true'); return false;">View Transactions</button>
                    </div>

                    <!-- hidden transactions for this project (kept compact) -->
                    <div id="tx-{{pid}}" class="transactions tx-small" aria-hidden="true" style="margin-top:12px;padding-top:12px;">
                        <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-bottom:8px;">Transactions for <strong>{{pid}}</strong>:</div>
                        <div class="ledger-grid" style="margin-top:6px;">
                                {% for block in chain %}
                                    {% if block.data is mapping and block.data.get('project_id') == pid %}
                                        <div class="tx-card" data-hash="{{block.hash}}" style="animation-delay: {{loop.index0 * 0.04}}s" onclick="this.classList.toggle('expanded')">
                                            <div class="tx-header">
                                                <div class="tx-title">🔹 {{block.data.get('action','Block')}}</div>
                                                <div class="tx-time">{{block.timestamp}}</div>
                                            </div>

                                            <div class="tx-body">
                                                <dl class="tx-details">
                                                    {% for k,v in block.data.items() %}
                                                        <dt>{{k}}</dt><dd>{{v}}</dd>
                                                    {% endfor %}
                                                </dl>
                                            </div>

                                            <div class="tx-footer">
                                                <div class="muted">prev: {{block.previous_hash[:12]}}...</div>
                                                <div>
                                                    <span class="hash">hash: {{block.hash[:12]}}...</span>
                                                    <button class="copy-btn" onclick="copyHash('{{block.hash}}', event)">Copy</button>
                                                </div>
                                            </div>
                                        </div>
                                    {% endif %}
                                {% endfor %}
                            </div>
                    </div>
                </div>
            {% endfor %}
        </div>

        <div class="global-ledger">
            <div class="ledger-header">
                <h2 style="margin:0">⛓ Blockchain Ledger</h2>
                <div style="display:flex;gap:8px;align-items:center;">
                    <input id="ledgerSearch" class="ledger-search" placeholder="Search action / project id / recipient..." />
                    <button class="btn btn-blue" onclick="resetSearch()">Reset</button>
                </div>
            </div>

            <div id="ledgerCards" class="ledger-cards" aria-live="polite">
                {% for block in chain %}
                    <div class="ledger-card" data-index="{{block.index}}" data-action="{% if block.data is mapping %}{{block.data.get('action','')|lower}}{% else %}{% endif %}" data-pid="{% if block.data is mapping %}{{block.data.get('project_id','')|lower}}{% endif %}" data-recipient="{% if block.data is mapping and block.data.get('details') %}{{ (block.data.details.to if block.data.details is mapping else '') | lower }}{% endif %}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                            <div style="display:flex;align-items:center;gap:10px;">
                                <div style="font-size:20px;">🔐</div>
                                <div>
                                    <div style="font-weight:800; font-size:15px; color:#fff;">Block {{block.index}}</div>
                                    <div style="font-size:12px; color:rgba(255,255,255,0.7)">{{block.timestamp}}</div>
                                </div>
                            </div>

                            <div style="text-align:right;">
                                {% if block.data is mapping %}
                                    {% set act = block.data.get('action','') %}
                                    <span class="action-badge {% if 'Project' in act %}badge-created{% elif 'Milestone' in act %}badge-milestone{% elif 'Payment' in act %}badge-payment{% else %}badge-created{% endif %}">{{act}}</span>
                                {% else %}
                                    <span class="action-badge badge-created">Info</span>
                                {% endif %}
                            </div>
                        </div>

                        <div style="margin-top:10px;">
                            {% if block.data is mapping %}
                                {% for k,v in block.data.items() %}
                                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed rgba(255,255,255,0.03);">
                                        <div style="color:rgba(255,255,255,0.75);font-weight:700">{{k}}</div>
                                        <div style="color:#e6f0ff;max-width:55%;text-align:right;word-break:break-word;">{{v}}</div>
                                    </div>
                                {% endfor %}
                            {% else %}
                                <div class="small-note">{{block.data}}</div>
                            {% endif %}
                        </div>

                        <div class="ledger-meta">
                            <div class="hash">prev: {{block.previous_hash[:16]}}...</div>
                            <div>
                                <span class="hash">hash: {{block.hash[:16]}}...</span>
                                <button class="copy-btn" onclick="copyHash('{{block.hash}}', event)">Copy</button>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        {% endif %}

        <script>
                // keep existing helpers
                 function copyHash(h, e){ e.stopPropagation(); if(navigator.clipboard){ navigator.clipboard.writeText(h).then(()=>{ toast('Hash copied'); }); } else { toast('Copy not supported'); } }
                 function resetSearch(){ document.getElementById('ledgerSearch').value=''; filterLedger(); }
                 document.addEventListener('DOMContentLoaded', ()=>{ const s = document.getElementById('ledgerSearch'); if(s) s.addEventListener('input', filterLedger); animateProgressBars(); });
                 function filterLedger(){
                     const q = document.getElementById('ledgerSearch').value.toLowerCase().trim();
                     document.querySelectorAll('#ledgerCards .ledger-card').forEach(card=>{
                         const text = ((card.dataset.action||'') + ' ' + (card.dataset.pid||'') + ' ' + (card.dataset.recipient||'')).toLowerCase();
                         card.style.display = (!q || text.includes(q)) ? '' : 'none';
                     });
                 }
                 
                 // Fix for JavaScript code (this was leftover from old app)
                 function toast(msg){ }

                // small toast helper
                function toast(msg){ const el = document.createElement('div'); el.innerText = msg; el.style.position='fixed'; el.style.right='18px'; el.style.bottom='18px'; el.style.padding='10px 14px'; el.style.background='rgba(2,6,23,0.9)'; el.style.color='#fff'; el.style.borderRadius='10px'; el.style.boxShadow='0 8px 24px rgba(2,6,23,0.6)'; document.body.appendChild(el); setTimeout(()=>el.style.opacity='0',1400); setTimeout(()=>document.body.removeChild(el),2000); }

                // animate progress bars from 0 to their target (use aria-valuenow or inline style value present)
                function animateProgressBars(){ document.querySelectorAll('.project-compact').forEach(card=>{
                    const bar = card.querySelector('.progress-bar');
                    if(!bar) return; // calculate target width from inline style if present, else from aria
                    let target = 0;
                    const styleWidth = bar.getAttribute('style');
                    if(styleWidth){ const m = styleWidth.match(/width:\s*([0-9.]+)%/); if(m) target = parseFloat(m[1]); }
                    if(!target){ const parent = card.querySelector('[aria-valuenow]'); if(parent) target = parseFloat(parent.getAttribute('aria-valuenow')||0); }
                    if(!target) target = 0;
                    // start from 6% for nicer animation
                    bar.style.width = '6%';
                    setTimeout(()=>{ bar.style.width = target + '%'; }, 120 + (Math.random()*200));
                })}

                // allow clicking copy button without toggling parent tx-card
                document.addEventListener('click', function(e){
                    if(e.target && e.target.classList.contains('copy-btn')) {
                        // handled in copyHash; prevent further propagation
                        e.stopPropagation();
                    }
                });
            </script>

     </div>

     <footer>
         © 2026 Transparency Blockchain Prototype | AI Powered Fraud Detection
     </footer>

 </body>
 </html>
 """

    # compute project analytics for the analysis panel
    total_projects = len(projects)
    completed_projects = sum(1 for p in projects.values() if (p.released_amount >= p.total_budget) or (len(p.completed_milestones) == len(p.milestones)))
    active_projects = total_projects - completed_projects
    total_budget = sum(p.total_budget for p in projects.values()) if projects else 0
    total_released = sum(p.released_amount for p in projects.values()) if projects else 0
    avg_release_pct = round((total_released / total_budget * 100), 2) if total_budget else 0
    contractors_count = len(contractors)

    project_stats = {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "total_budget": total_budget,
        "total_released": total_released,
        "avg_release_pct": avg_release_pct,
        "contractors_count": contractors_count
    }

    return render_template_string(
        html,
        projects=projects,
        chain=blockchain.chain,
        role=role,
        available_contractors=available_contractors,
        project_stats=project_stats,
        contractors=contractors,
        funding_requests=funding_requests,
        fund_requests=fund_requests,
        work_logs=work_logs,
        ratings=ratings
    )


# ---------------------------
# VALIDATE
# ---------------------------
@app.route("/validate")
def validate():
    return jsonify({"Blockchain Valid": blockchain.is_chain_valid()})


if __name__ == "__main__":
    # Bind to all interfaces so the app is reachable from localhost and other hosts
    print("Starting Transparency Dashboard with SocketIO on http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=8000, debug=True)