from flask import Blueprint, render_template_string, request, jsonify, url_for
import os
import base64
import io
from datetime import datetime
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
from .blockchain_xray import Blockchain
from . import image as detection_module
from modules.extensions import socketio

ai_bp = Blueprint("ai", __name__, template_folder="templates")

blockchain = Blockchain()
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "mp4", "avi"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@ai_bp.route("/")
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
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0a0e27 0%, #1a0033 100%); color: #e6f6ff; overflow-x: hidden; }
            header { background: linear-gradient(90deg, rgba(0, 212, 255, 0.1), rgba(0, 100, 150, 0.1)); padding: 20px; text-align: center; border-bottom: 2px solid var(--primary); box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2); }
            h1 { font-size: 28px; color: var(--primary); text-shadow: 0 0 10px rgba(0, 212, 255, 0.5); margin-bottom: 10px; }
            .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }
            .camera-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
            @media (max-width: 1024px) { .camera-grid { grid-template-columns: 1fr; } }
            .camera-card { background: var(--card-bg); border: 2px solid var(--primary); border-radius: 15px; padding: 15px; box-shadow: 0 0 20px rgba(0, 212, 255, 0.3), inset 0 0 10px rgba(0, 212, 255, 0.1); }
            .camera-label { color: var(--primary); font-weight: bold; margin-bottom: 10px; text-transform: uppercase; font-size: 14px; letter-spacing: 2px; }
            video, canvas { width: 100%; height: auto; border-radius: 10px; background: #000; display: block; }
            .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat-box { background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(100, 150, 200, 0.1)); border: 1px solid var(--primary); border-radius: 10px; padding: 15px; text-align: center; }
            .stat-value { font-size: 24px; color: var(--success); font-weight: bold; }
            .stat-label { color: #aaa; font-size: 12px; margin-top: 5px; }
            .controls { text-align: center; margin-bottom: 30px; }
            button { padding: 12px 30px; margin: 0 10px; font-size: 14px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.3s; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); }
            .btn-start { background: linear-gradient(135deg, var(--success), #00cc66); color: #000; }
            .btn-stop { background: linear-gradient(135deg, var(--danger), #cc0000); color: #fff; }
            .threat-log { background: var(--card-bg); border: 2px solid var(--danger); border-radius: 15px; padding: 20px; margin-top: 30px; max-height: 400px; overflow-y: auto; }
            .threat-entry { background: rgba(255, 51, 51, 0.1); border-left: 4px solid var(--danger); padding: 10px; margin-bottom: 10px; border-radius: 5px; font-size: 13px; }
            .threat-time { color: var(--warning); font-weight: bold; }
            .threat-item { color: var(--danger); font-weight: bold; margin-top: 5px; }
            .confidence { color: var(--primary); font-size: 12px; margin-top: 3px; }
            .upload-section { background: var(--card-bg); border: 2px dashed var(--primary); border-radius: 15px; padding: 30px; text-align: center; margin-top: 30px; }
            .upload-section h3 { color: var(--primary); margin-bottom: 15px; }
            input[type="file"] { padding: 10px; margin: 10px 0; background: rgba(0, 212, 255, 0.1); border: 1px solid var(--primary); border-radius: 8px; color: #fff; cursor: pointer; }
            .scrollbar-hide::-webkit-scrollbar { display: none; }
            .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
            .top-nav { display:flex; justify-content:space-between; align-items:center; gap:14px; }
            .top-nav a { color: var(--primary); text-decoration:none; border:1px solid var(--primary); padding:8px 14px; border-radius:10px; }
        </style>
    </head>
    <body>
        <header>
            <div class="top-nav">
                <div>
                    <h1>🔍 X-RAY THREAT SCANNER</h1>
                    <p>Real-time Security Screening System with AI Threat Detection</p>
                </div>
                <div><a href="{{ url_for('ai.blockchain_page') }}">⛓ View Blockchain</a></div>
            </div>
        </header>

        <div class="container">
            <div class="controls">
                <button class="btn-start" onclick="startScanning()">START DUAL SCANNING</button>
                <button class="btn-stop" onclick="stopScanning()">STOP SCANNING</button>
            </div>
            <div class="camera-grid">
                <div class="camera-card">
                    <div class="camera-label">Camera 1 Input</div>
                    <video id="video1" autoplay muted playsinline></video>
                </div>
                <div class="camera-card">
                    <div class="camera-label">Camera 2 Input</div>
                    <video id="video2" autoplay muted playsinline></video>
                </div>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-value" id="threatCount">0</div><div class="stat-label">Detected Threats</div></div>
                <div class="stat-box"><div class="stat-value" id="scanStatus">Stopped</div><div class="stat-label">Scan Status</div></div>
                <div class="stat-box"><div class="stat-value" id="lastUpdate">--</div><div class="stat-label">Last Update</div></div>
            </div>
            <div class="upload-section">
                <h3>Upload Image for Threat Analysis</h3>
                <input type="file" id="imageUpload" accept="image/*">
                <button class="btn-start" onclick="uploadImage()">Analyze Image</button>
            </div>
            <div class="threat-log" id="threatLog"></div>
        </div>

        <script>
            let scanning = false;
            let scanInterval = null;

            function startScanning() {
                if (scanning) return;
                scanning = true;
                document.getElementById('scanStatus').innerText = 'Running';
                scanInterval = setInterval(captureFrame, 1500);
            }

            function stopScanning() {
                scanning = false;
                document.getElementById('scanStatus').innerText = 'Stopped';
                clearInterval(scanInterval);
            }

            async function uploadImage() {
                const fileInput = document.getElementById('imageUpload');
                if (!fileInput.files.length) {
                    alert('Please select an image file.');
                    return;
                }
                const formData = new FormData();
                formData.append('image', fileInput.files[0]);
                const response = await fetch('upload', { method: 'POST', body: formData });
                const result = await response.json();
                if (result.success) {
                    appendThreats(result.detections, result.message);
                } else {
                    appendThreats([], result.error || 'Unknown error');
                }
            }

            async function captureFrame() {
                if (!scanning) return;
                const video = document.getElementById('video1');
                if (!video || video.readyState < 2) return;
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                canvas.toBlob(async (blob) => {
                    const formData = new FormData();
                    formData.append('frame', blob, 'frame.jpg');
                    const response = await fetch('detect_dual', { method: 'POST', body: formData });
                    const data = await response.json();
                    appendThreats(data.detections || [], data.success ? 'Real-time scan complete' : 'Scan failed');
                }, 'image/jpeg');
            }

            function appendThreats(detections, message) {
                const log = document.getElementById('threatLog');
                const now = new Date().toLocaleTimeString();
                document.getElementById('threatCount').innerText = detections.length;
                document.getElementById('lastUpdate').innerText = now;
                const item = document.createElement('div');
                item.className = 'threat-entry';
                item.innerHTML = `<div class="threat-time">${now}</div><div class="threat-item">${message}</div>`;
                if (detections.length) {
                    detections.forEach(d => {
                        item.innerHTML += `<div class="confidence">${d.item} (${d.severity}) — confidence ${d.confidence}</div>`;
                    });
                }
                log.prepend(item);
            }

            async function startCamera() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                    document.getElementById('video1').srcObject = stream;
                    document.getElementById('video2').srcObject = stream;
                } catch (error) {
                    console.warn('Camera access denied or unavailable', error);
                }
            }

            startCamera();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@ai_bp.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image_file = request.files['image']
    if not allowed_file(image_file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        filename = secure_filename(f"upload_{datetime.now().timestamp()}_{image_file.filename}")
        filepath = os.path.join(UPLOAD_ROOT, filename)
        image_file.save(filepath)
        result = detection_module.detect_threats(filepath)
        if isinstance(result, dict) and 'detections' in result:
            detections = result['detections']
            annotated_frame = result.get('annotated_frame')
        else:
            detections = result if isinstance(result, list) else []
            annotated_frame = None

        formatted_detections = []
        for detection in detections:
            formatted_detections.append({
                'item': detection.get('item', 'Unknown'),
                'severity': detection.get('severity', 'UNKNOWN'),
                'confidence': detection.get('confidence', 0.0),
                'bbox': detection.get('bbox', []),
                'color': detection.get('color', '#FF0000')
            })

        annotated_image_base64 = None
        if annotated_frame is not None:
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            annotated_image_base64 = base64.b64encode(buffer).decode('utf-8')

        original_image_base64 = None
        try:
            with open(filepath, 'rb') as img_file:
                original_image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        except Exception:
            pass

        blockchain.add_block({
            'action': 'Image Scan',
            'filename': filename,
            'timestamp': datetime.now().isoformat(),
            'detections': formatted_detections,
            'total_threats': len(formatted_detections),
            'original_image': original_image_base64,
            'annotated_image': annotated_image_base64
        })

        return jsonify({
            'success': True,
            'detections': formatted_detections,
            'filename': filename,
            'total_threats': len(formatted_detections),
            'message': f"Analysis complete. Found {len(formatted_detections)} potential threat(s).",
            'annotated_image': annotated_image_base64
        })
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@ai_bp.route('/detect', methods=['POST'])
def detect():
    if 'frame' not in request.files:
        return jsonify({'error': 'No frame provided'}), 400

    frame = request.files['frame']
    frame_data = frame.read()
    img = Image.open(io.BytesIO(frame_data))
    temp_path = os.path.join(UPLOAD_ROOT, 'temp_frame.jpg')
    img.save(temp_path)
    result = detection_module.detect_threats(temp_path)
    if isinstance(result, dict) and 'detections' in result:
        detections = result['detections']
    else:
        detections = result if isinstance(result, list) else []
    return jsonify({'success': True, 'detections': detections})

@ai_bp.route('/detect_dual', methods=['POST'])
def detect_dual():
    if 'frame' not in request.files:
        return jsonify({'error': 'No frame provided'}), 400

    try:
        frame_file = request.files['frame']
        frame_data = frame_file.read()
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'detections': []})
        result = detection_module.detect_threats_from_frame(frame, 'stream')
        detections = result.get('detections', [])
        threat_detections = [d for d in detections if d.get('severity') in ['CRITICAL', 'HIGH', 'SCANNING']]
        return jsonify({'success': True, 'detections': threat_detections})
    except Exception as e:
        print(f"Dual detection error: {e}")
        return jsonify({'success': False, 'detections': [], 'error': str(e)})

@ai_bp.route('/blockchain')
def blockchain_page():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>⛓ Blockchain Ledger</title>
        <style>
            :root { --primary: #00d4ff; --danger: #ff3333; --success: #00ff88; --dark-bg: #0a0e27; --card-bg: #1a1f3a; --text-light: #e0e0e0; --text-muted: #888; }
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family:'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, var(--dark-bg) 0%, #0f1629 100%); color: var(--text-light); }
            .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
            header { text-align:center; margin-bottom:30px; border-bottom:2px solid var(--primary); padding-bottom:20px; }
            h1 { font-size:2.2em; color: var(--primary); text-shadow:0 0 20px rgba(0,212,255,0.5); }
            .nav { text-align:center; margin-bottom:30px; }
            .nav a { color: var(--primary); text-decoration:none; padding:10px 18px; border:1px solid var(--primary); border-radius:8px; transition: all 0.3s; }
            .nav a:hover { background: var(--primary); color: #000; }
            .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:15px; margin-bottom:30px; }
            .stat-box { background: rgba(0,212,255,0.1); border:1px solid var(--primary); border-radius:8px; padding:15px; text-align:center; }
            .ledger-cards { display:grid; gap:16px; }
            .ledger-card { padding:16px; border-radius:14px; background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); }
            .ledger-card h2 { margin:0 0 10px 0; }
            .ledger-meta { display:flex; justify-content:space-between; gap:10px; font-size:12px; color: rgba(224, 224, 224, 0.8); margin-top:12px; }
            .hash { font-family:monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>⛓ AI-XBS Scan Blockchain Ledger</h1>
                <p>Immutable record for X-ray analyses and threat detection events.</p>
            </header>
            <div class="nav"><a href="{{ url_for('ai.index') }}">Back to Scanner</a></div>
            <div class="ledger-cards">
                {% for block in chain %}
                    <div class="ledger-card">
                        <h2>Block {{ block.index }} - {{ block.timestamp }}</h2>
                        {% if block.data is mapping %}
                            <div><strong>Action</strong>: {{ block.data.get('action', 'Unknown') }}</div>
                            {% for key, value in block.data.items() %}
                                <div><strong>{{ key }}</strong>: {{ value }}</div>
                            {% endfor %}
                        {% else %}
                            <div>{{ block.data }}</div>
                        {% endif %}
                        <div class="ledger-meta">
                            <span>Prev: {{ block.previous_hash[:16] }}...</span>
                            <span class="hash">Hash: {{ block.hash[:16] }}...</span>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, chain=blockchain.chain)
