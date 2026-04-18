from flask import Flask, render_template_string, request, jsonify
print("DEBUG: Starting app.py - FILE LOADED")
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import base64
import threading
import json
import os
import sys
import importlib.util
p0017_dir = os.path.dirname(__file__)
p0017_image_path = os.path.join(p0017_dir, "image.py")
spec = importlib.util.spec_from_file_location("p0017_image", p0017_image_path)
detection_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detection_module)
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import io
from blockchain import Blockchain

app = Flask(__name__)
print("DEBUG: Flask app created!")
app.secret_key = "xray-scanner-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*")
blockchain = Blockchain()

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
            }

            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #1a0033 100%);
                color: #e6f6ff;
                overflow-x: hidden;
            }

            header {
                background: linear-gradient(90deg, rgba(0, 212, 255, 0.1), rgba(0, 100, 150, 0.1));
                padding: 20px;
                text-align: center;
                border-bottom: 2px solid var(--primary);
                box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
            }

            h1 {
                font-size: 28px;
                color: var(--primary);
                text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
                margin-bottom: 10px;
            }

            .container {
                max-width: 1400px;
                margin: 20px auto;
                padding: 0 20px;
            }

            .camera-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }

            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }

            .threat-alert {
                animation: slideIn 0.5s ease-out;
            }

            .camera-card {
                background: var(--card-bg);
                border: 2px solid var(--primary);
                border-radius: 15px;
                padding: 15px;
                box-shadow: 0 0 20px rgba(0, 212, 255, 0.3), inset 0 0 10px rgba(0, 212, 255, 0.1);
            }

            .camera-label {
                color: var(--primary);
                font-weight: bold;
                margin-bottom: 10px;
                text-transform: uppercase;
                font-size: 14px;
                letter-spacing: 2px;
            }

            video, canvas {
                width: 100%;
                height: auto;
                border-radius: 10px;
                background: #000;
                display: block;
            }

            .stats-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }

            .stat-box {
                background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(100, 150, 200, 0.1));
                border: 1px solid var(--primary);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
            }

            .stat-value {
                font-size: 24px;
                color: var(--success);
                font-weight: bold;
            }

            .stat-label {
                color: #aaa;
                font-size: 12px;
                margin-top: 5px;
            }

            .controls {
                text-align: center;
                margin-bottom: 30px;
            }

            button {
                padding: 12px 30px;
                margin: 0 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            }

            .btn-start {
                background: linear-gradient(135deg, var(--success), #00cc66);
                color: #000;
            }

            .btn-start:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0, 255, 136, 0.4); }

            .btn-stop {
                background: linear-gradient(135deg, var(--danger), #cc0000);
                color: #fff;
            }

            .btn-stop:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(255, 51, 51, 0.4); }

            .threat-log {
                background: var(--card-bg);
                border: 2px solid var(--danger);
                border-radius: 15px;
                padding: 20px;
                margin-top: 30px;
                max-height: 400px;
                overflow-y: auto;
            }

            .threat-entry {
                background: rgba(255, 51, 51, 0.1);
                border-left: 4px solid var(--danger);
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 5px;
                font-size: 13px;
            }

            .threat-time {
                color: var(--warning);
                font-weight: bold;
            }

            .threat-item {
                color: var(--danger);
                font-weight: bold;
                margin-top: 5px;
            }

            .confidence {
                color: var(--primary);
                font-size: 12px;
                margin-top: 3px;
            }

            .upload-section {
                background: var(--card-bg);
                border: 2px dashed var(--primary);
                border-radius: 15px;
                padding: 30px;
                text-align: center;
                margin-top: 30px;
            }

            .upload-section h3 {
                color: var(--primary);
                margin-bottom: 15px;
            }

            input[type="file"] {
                padding: 10px;
                margin: 10px 0;
                background: rgba(0, 212, 255, 0.1);
                border: 1px solid var(--primary);
                border-radius: 8px;
                color: #fff;
                cursor: pointer;
            }

            .scrollbar-hide::-webkit-scrollbar { display: none; }
            .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
        </style>
    </head>
    <body>
        <header>
            <h1>🔍 X-RAY THREAT SCANNER</h1>
            <p>Real-time Security Screening System with AI Threat Detection</p>
            <nav style="margin-top: 15px; display:flex; justify-content:center; flex-wrap:wrap; gap:10px;">
                <a href="/blockchain" style="color: var(--primary); text-decoration: none; padding: 8px 16px; border: 1px solid var(--primary); border-radius: 5px; transition: all 0.3s;">⛓ View Blockchain</a>
                <a href="/logout" style="color: #fff; background: var(--primary); text-decoration: none; padding: 8px 16px; border-radius: 5px; transition: all 0.3s;">← Back to SSS Dashboard</a>
            </nav>
        </header>

        <div class="container">
            <div class="controls">
                <button class="btn-start" onclick="startScanning()">START DUAL SCANNING</button>
                <button class="btn-stop" onclick="stopScanning()">STOP SCANNING</button>
            </div>

            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-value" id="threat-count">0</div>
                    <div class="stat-label">THREATS DETECTED</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="scan-status">READY</div>
                    <div class="stat-label">SCAN STATUS</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="frame-count">0</div>
                    <div class="stat-label">FRAMES PROCESSED</div>
                </div>
            </div>

            <div class="camera-grid">
                <div class="camera-card">
                    <div class="camera-label">📹 NORMAL CAMERA</div>
                    <video id="video-normal" autoplay playsinline muted></video>
                </div>
                <div class="camera-card">
                    <div class="camera-label">🔍 X-RAY SCANNER</div>
                    <canvas id="canvas-xray"></canvas>
                </div>
            </div>

            <div class="threat-log scrollbar-hide" id="threat-log">
                <h3 style="color: var(--danger); margin-bottom: 15px;">⚠️ THREAT LOG</h3>
                <div id="log-entries" style="color: #aaa;">No threats detected yet...</div>
            </div>

            <div class="upload-section">
                <h3>📤 Upload Image for Analysis</h3>
                <form id="uploadForm" action="/upload" method="POST" enctype="multipart/form-data">
                    <input type="file" id="uploadFile" name="image" accept="image/*" required>
                    <button type="submit" class="btn-start">ANALYZE IMAGE WITH AI</button>
                </form>
                <div id="uploadResult" style="margin-top: 15px; color: var(--primary);"></div>
            </div>
        </div>

        <script>
            const socket = io();
            let scanning = false;
            let frameCount = 0;
            let threatCount = 0;
            const threats = [];

            async function startScanning() {
                scanning = true;
                document.getElementById('scan-status').textContent = 'SCANNING';
                document.getElementById('scan-status').style.color = 'var(--success)';
                
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
                    const videoElement = document.getElementById('video-normal');
                    videoElement.srcObject = stream;
                    
                    videoElement.onloadedmetadata = () => {
                        captureFrames();
                    };
                } catch (error) {
                    console.error('Camera access error:', error);
                    alert('Unable to access camera. Please check permissions.');
                    scanning = false;
                    document.getElementById('scan-status').textContent = 'ERROR';
                    document.getElementById('scan-status').style.color = 'var(--danger)';
                }
            }

            function stopScanning() {
                scanning = false;
                document.getElementById('scan-status').textContent = 'STOPPED';
                document.getElementById('scan-status').style.color = 'var(--warning)';
                const videoElement = document.getElementById('video-normal');
                if (videoElement.srcObject) {
                    videoElement.srcObject.getTracks().forEach(track => track.stop());
                }
            }

            function captureFrames() {
                if (!scanning) return;
                
                const videoElement = document.getElementById('video-normal');
                const canvasXray = document.getElementById('canvas-xray');
                const ctx = canvasXray.getContext('2d');
                
                canvasXray.width = videoElement.videoWidth;
                canvasXray.height = videoElement.videoHeight;
                
                ctx.drawImage(videoElement, 0, 0);
                
                const imageData = ctx.getImageData(0, 0, canvasXray.width, canvasXray.height);
                const xrayEffect = applyXrayEffect(imageData);
                ctx.putImageData(xrayEffect, 0, 0);
                
                frameCount++;
                document.getElementById('frame-count').textContent = frameCount;
                
                // Send frame for detection every 2 frames
                if (frameCount % 2 === 0) {
                    canvasXray.toBlob(blob => {
                        uploadFrame(blob);
                    }, 'image/jpeg', 0.6);
                }
                
                requestAnimationFrame(captureFrames);
            }

            function applyXrayEffect(imageData) {
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
                    const inverted = 255 - gray;
                    
                    data[i] = Math.max(0, inverted * 0.3);        // Red
                    data[i + 1] = Math.min(255, inverted * 1.3);  // Green
                    data[i + 2] = Math.max(0, inverted * 0.5);    // Blue
                    data[i + 3] = 255;                             // Alpha
                }
                return imageData;
            }

            async function uploadFrame(blob) {
                try {
                    const formData = new FormData();
                    formData.append('frame', blob, 'frame.jpg');

                    const response = await fetch('/detect_dual', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();
                    console.log('Dual camera detection result:', result); // Debug logging

                    if (result.threat_found && result.detections && result.detections.length > 0) {
                        // Enhanced threat detection with alerts
                        result.detections.forEach(detection => {
                            // Check for duplicate threats (same item within last 2 seconds)
                            const now = new Date();
                            const recentThreat = threats.find(t =>
                                t.item === detection.item &&
                                (now - new Date(t.timestamp.replace(' ', 'T'))) < 2000
                            );

                            if (!recentThreat) {
                                const threatEntry = {
                                    item: detection.item,
                                    severity: detection.severity,
                                    confidence: (detection.confidence * 100).toFixed(1),
                                    timestamp: new Date().toLocaleTimeString(),
                                    camera: 'dual_stream'
                                };

                                threats.unshift(threatEntry);
                                threatCount++;

                                // Visual alert for critical threats
                                if (detection.severity === 'CRITICAL') {
                                    showThreatAlert(`🚨 CRITICAL THREAT: ${detection.item.toUpperCase()} detected!`, 'danger');
                                    // Add red border flash effect
                                    document.body.style.border = '5px solid red';
                                    setTimeout(() => document.body.style.border = '', 1000);
                                } else if (detection.severity === 'HIGH') {
                                    showThreatAlert(`⚠️ HIGH THREAT: ${detection.item} detected!`, 'warning');
                                }

                                updateThreatLog();
                                console.log(`🚨 THREAT LOGGED: ${detection.item} (${detection.severity}) - ${threatEntry.confidence}% confidence`);
                            }
                        });
                    } else if (result.safety_status) {
                        // Show safety message when no threats detected
                        console.log('Safety Status:', result.safety_status);
                        // Update safety indicator
                        updateSafetyIndicator(result.safety_status);
                    }

                    // Update stats
                    document.getElementById('frame-count').textContent = frameCount;

                } catch (error) {
                    console.error('Upload error:', error);
                }
            }

            function showThreatAlert(message, type) {
                // Create alert element
                const alertDiv = document.createElement('div');
                alertDiv.className = `threat-alert ${type}`;
                alertDiv.innerHTML = `
                    <div style="
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        background: ${type === 'danger' ? '#ff3333' : '#ffaa00'};
                        color: white;
                        padding: 15px 20px;
                        border-radius: 10px;
                        font-weight: bold;
                        font-size: 16px;
                        z-index: 10000;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                        animation: slideIn 0.5s ease-out;
                    ">
                        ${message}
                    </div>
                `;

                document.body.appendChild(alertDiv);

                // Remove after 3 seconds
                setTimeout(() => {
                    alertDiv.style.animation = 'slideOut 0.5s ease-in';
                    setTimeout(() => document.body.removeChild(alertDiv), 500);
                }, 3000);
            }

            function updateSafetyIndicator(status) {
                const indicator = document.getElementById('safety-indicator') || createSafetyIndicator();
                indicator.textContent = status;
                indicator.style.color = status.includes('SAFE') ? 'var(--success)' : 'var(--danger)';
            }

            function createSafetyIndicator() {
                const indicator = document.createElement('div');
                indicator.id = 'safety-indicator';
                indicator.style.cssText = `
                    position: fixed;
                    top: 80px;
                    right: 20px;
                    font-size: 14px;
                    font-weight: bold;
                    z-index: 1000;
                `;
                document.body.appendChild(indicator);
                return indicator;
            }

            function updateThreatLog() {
                document.getElementById('threat-count').textContent = threatCount;
                const logEntries = document.getElementById('log-entries');

                if (threats.length === 0) {
                    logEntries.innerHTML = '<div style="color: var(--success); font-weight: bold; text-align: center; padding: 20px; background: rgba(0, 255, 136, 0.1); border: 2px solid var(--success); border-radius: 10px;">✅ ALL FRAMES ARE SAFE - NO THREATS DETECTED</div>';
                    return;
                }

                logEntries.innerHTML = threats.slice(0, 10).map(t => {
                    const severityColor = t.severity === 'CRITICAL' ? 'var(--danger)' :
                                        t.severity === 'HIGH' ? 'var(--warning)' : 'var(--primary)';
                    const severityIcon = t.severity === 'CRITICAL' ? '🚨' :
                                       t.severity === 'HIGH' ? '⚠️' : '🔍';

                    return `
                        <div class="threat-entry" style="border-left: 4px solid ${severityColor}; background: rgba(255, 51, 51, 0.1);">
                            <div class="threat-time" style="color: #aaa; font-size: 12px;">${t.timestamp}</div>
                            <div class="threat-item" style="color: ${severityColor}; font-weight: bold; font-size: 16px;">
                                ${severityIcon} ${t.item.toUpperCase()}
                            </div>
                            <div class="confidence" style="color: #fff; font-weight: bold;">
                                Severity: <span style="color: ${severityColor};">${t.severity}</span> |
                                Confidence: <span style="color: var(--success);">${t.confidence}%</span>
                            </div>
                            <div style="font-size: 11px; color: #888; margin-top: 5px;">
                                Camera: ${t.camera || 'unknown'}
                            </div>
                        </div>
                    `;
                }).join('');

                // Add summary if there are more threats
                if (threats.length > 10) {
                    logEntries.innerHTML += `<div style="text-align: center; padding: 10px; color: var(--warning); font-style: italic;">
                        ... and ${threats.length - 10} more threats detected
                    </div>`;
                }
            }

            // Image upload handler
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const file = document.getElementById('uploadFile').files[0];
                if (!file) return;
                
                const resultDiv = document.getElementById('uploadResult');
                resultDiv.innerHTML = '<div style="color: var(--primary);">🔍 Analyzing image...</div>';
                
                const formData = new FormData();
                formData.append('image', file);
                
                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    console.log('upload result', result);
                    
                    if (result.success && result.detections && result.detections.length > 0) {
                        let html = `<div style="color: var(--success); margin-bottom: 15px; font-size: 16px; font-weight: bold;">✅ ${result.message}</div>`;
                        
                        // Display annotated image if available
                        if (result.annotated_image) {
                            html += `
                                <div style="margin-bottom: 20px; border: 2px solid var(--primary); border-radius: 10px; overflow: hidden; background: #000;">
                                    <img src="data:image/jpeg;base64,${result.annotated_image}" 
                                         style="width: 100%; height: auto; display: block; max-height: 500px; object-fit: contain;">
                                </div>
                            `;
                        }
                        
                        html += '<div style="color: var(--primary); font-weight: bold; margin-bottom: 10px;">🔴 DETECTION DETAILS:</div>';
                        
                        result.detections.forEach((detection, idx) => {
                            const confidencePercent = (detection.confidence * 100).toFixed(1);
                            const severityColor = getSeverityColor(detection.severity);
                            
                            html += `
                                <div style="background: rgba(255, 51, 51, 0.1); border-left: 5px solid ${severityColor}; padding: 12px; margin-bottom: 10px; border-radius: 5px;">
                                    <div style="font-weight: bold; color: ${severityColor}; font-size: 16px; margin-bottom: 5px;">
                                        #${idx+1} - ⚠️ ${detection.item.toUpperCase()}
                                    </div>
                                    <div style="color: var(--warning); margin: 5px 0;">
                                        🔴 Severity: <strong>${detection.severity}</strong>
                                    </div>
                                    <div style="color: var(--primary); margin: 5px 0;">
                                        📊 Confidence Score: <strong>${confidencePercent}%</strong>
                                    </div>
                                    <div style="font-size: 12px; color: #aaa; margin-top: 8px;">
                                        Risk Assessment: ${getThreatLevel(detection.severity, confidencePercent)}
                                    </div>
                                </div>
                            `;
                        });
                        
                        resultDiv.innerHTML = html;
                    } else if (result.success) {
                        const safetyMessage = result.safety_status || '✅ No threats detected in uploaded image - IMAGE IS SAFE!';
                        resultDiv.innerHTML = `<div style="color: var(--success); font-size: 18px; font-weight: bold; padding: 20px; background: rgba(0, 255, 136, 0.1); border: 2px solid var(--success); border-radius: 10px; text-align: center;">${safetyMessage}</div>`;
                    } else {
                        const errorMessage = result.error || 'Error analyzing image. Please try again.';
                        resultDiv.innerHTML = `<div style="color: var(--danger);">❌ ${errorMessage}</div>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = '<div style="color: var(--danger);">❌ Error analyzing image. Please try again.</div>';
                    console.error('Upload error:', error);
                }
            });
            
            function getSeverityColor(severity) {
                switch(severity) {
                    case 'CRITICAL': return 'var(--danger)';
                    case 'HIGH': return 'var(--warning)';
                    case 'WARNING': return '#ff8800';
                    case 'SCANNING': return 'var(--primary)';
                    default: return '#888';
                }
            }
            
            function getThreatLevel(severity, confidence) {
                const conf = parseFloat(confidence);
                if (severity === 'CRITICAL' && conf > 70) return 'EXTREME - Immediate Action Required';
                if (severity === 'HIGH' && conf > 60) return 'HIGH - Security Alert';
                if (severity === 'WARNING' && conf > 50) return 'MEDIUM - Monitor Closely';
                if (severity === 'SCANNING') return 'LOW - Routine Check';
                return 'UNKNOWN - Further Analysis Needed';
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        debug_path = os.path.join(os.path.dirname(__file__), "debug.log")
        with open(debug_path, "a") as f:
            f.write("DEBUG: Upload route called!\n")
        image_file = request.files.get("image") or request.files.get("file")
        if not image_file:
            return jsonify({"error": "No image provided"}), 400
        
        if not allowed_file(image_file.filename):
            return jsonify({"error": "Invalid file type"}), 400
        
        try:
            # Save temporarily
            filename = secure_filename(f"upload_{datetime.now().timestamp()}_{image_file.filename}")
            filepath = os.path.join(UPLOAD_ROOT, filename)
            image_file.save(filepath)
            
            # Detect threats
            print(f"DEBUG: About to detect threats in {filepath}")
            result = detection_module.detect_threats(filepath)
            print(f"DEBUG: Detection result: {result}")
            
            # Ensure we return detections in the right format
            if isinstance(result, dict) and "detections" in result:
                detections = result["detections"]
                annotated_frame = result.get("annotated_frame")
            else:
                detections = result if isinstance(result, list) else []
                annotated_frame = None
            
            print(f"DEBUG: Final detections: {detections}")
            
            # Format detections for better display
            formatted_detections = []
            for detection in detections:
                formatted_detections.append({
                    "item": detection.get("item", "Unknown"),
                    "severity": detection.get("severity", "UNKNOWN"),
                    "confidence": detection.get("confidence", 0.0),
                    "bbox": detection.get("bbox", []),
                    "color": detection.get("color", "#FF0000")
                })
            
            # Convert annotated frame to base64 for display
            annotated_image_base64 = None
            if annotated_frame is not None:
                _, buffer = cv2.imencode('.jpg', annotated_frame)
                annotated_image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Read and convert original uploaded image to base64
            original_image_base64 = None
            try:
                with open(filepath, 'rb') as img_file:
                    original_image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            except:
                pass
            
            # Add scan to blockchain with image data (always store, whether threats found or not)
            blockchain.add_block({
                "action": "Image Scan",
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "detections": formatted_detections,
                "total_threats": len(formatted_detections),
                "safety_status": "SAFE" if len(formatted_detections) == 0 else "THREATS_DETECTED",
                "threat_found": len(formatted_detections) > 0,
                "original_image": original_image_base64,
                "annotated_image": annotated_image_base64
            })
            
            # Enhanced response message for safe images
            if len(formatted_detections) == 0:
                response_message = "✅ ANALYSIS COMPLETE - NO THREATS DETECTED. Image is safe and stored in blockchain."
                safety_status = "✅ IMAGE IS SAFE - NO THREATS DETECTED"
            else:
                response_message = f"⚠️ ANALYSIS COMPLETE - Found {len(formatted_detections)} potential threat(s)."
                safety_status = f"⚠️ {len(formatted_detections)} THREAT(S) DETECTED"
            
            return jsonify({
                "success": True,
                "detections": formatted_detections,
                "filename": filename,
                "total_threats": len(formatted_detections),
                "message": response_message,
                "safety_status": safety_status,
                "threat_found": len(formatted_detections) > 0,
                "blockchain_stored": True,
                "annotated_image": annotated_image_base64
            })
            
        except Exception as e:
            print(f"Error processing upload: {str(e)}")
            return jsonify({"error": f"Processing failed: {str(e)}"}), 500
            
    except Exception as outer_e:
        error_path = os.path.join(os.path.dirname(__file__), "debug_error.log")
        with open(error_path, "a") as f:
            f.write(f"OUTER DEBUG ERROR: {str(outer_e)}\n")
        return jsonify({"error": "Internal server error"}), 500

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
    
    # Add safety message when no threats detected
    safety_status = "safe"
    if len(detections) == 0:
        safety_status = "✅ IMAGE IS SAFE - NO THREATS DETECTED"
    
    return jsonify({
        "success": True,
        "detections": detections,
        "safety_status": safety_status,
        "threat_found": len(detections) > 0
    })

@app.route("/detect_dual", methods=["POST"])
def detect_dual():
    """
    Real-time threat detection with YOLOv8 for dual camera scanning.
    Enhanced to properly detect guns and knives with improved logging.
    """
    frame_file = request.files.get("frame") or request.files.get("file")
    if not frame_file:
        return jsonify({"error": "No frame provided"}), 400

    try:
        frame_data = frame_file.read()

        # Convert byte stream to OpenCV format
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"detections": []})

        # Run real object detection
        result = detection_module.detect_threats_from_frame(frame, "stream")
        detections = result.get("detections", [])

        # Filter for only threats (CRITICAL and HIGH severity)
        threat_detections = [d for d in detections if d.get("severity") in ["CRITICAL", "HIGH"]]

        # Enhanced safety status messages
        safety_status = "safe"
        threat_found = len(threat_detections) > 0

        if threat_found:
            # Log threats to global threat log
            global threat_log
            for detection in threat_detections:
                threat_entry = {
                    "item": detection.get("item", "Unknown"),
                    "severity": detection.get("severity", "UNKNOWN"),
                    "confidence": detection.get("confidence", 0),
                    "timestamp": detection.get("timestamp", datetime.now().isoformat()),
                    "camera": "dual_stream"
                }
                threat_log.append(threat_entry)
                print(f"🚨 THREAT DETECTED: {threat_entry['item']} (Severity: {threat_entry['severity']}, Confidence: {threat_entry['confidence']:.1%})")

            safety_status = f"🚨 THREAT DETECTED: {len(threat_detections)} dangerous item(s) found!"
        else:
            safety_status = "✅ FRAME IS SAFE - NO THREATS DETECTED"

        return jsonify({
            "success": True,
            "detections": threat_detections,
            "safety_status": safety_status,
            "threat_found": threat_found,
            "threat_count": len(threat_detections),
            "total_detections": len(detections)
        })
        print(f"Returning dual detection result: success={True}, threat_found={threat_found}, detections_count={len(threat_detections)}")

    except Exception as e:
        print(f"Dual detection error: {e}")
        return jsonify({
            "success": False,
            "detections": [],
            "error": str(e),
            "safety_status": "⚠️ SCANNING ERROR - Unable to process frame"
        })


@app.route("/threat_log")
def get_threat_log():
    """Get the current threat log as JSON"""
    return jsonify({
        "threats": threat_log[-50:],  # Last 50 threats
        "total_count": len(threat_log),
        "active_threats": len([t for t in threat_log if t.get("severity") in ["CRITICAL", "HIGH"]])
    })

@app.route("/blockchain")
def view_blockchain():
    """View the blockchain ledger"""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⛓ Blockchain Ledger</title>
    <style>
        :root {
            --primary: #00d4ff;
            --danger: #ff3333;
            --success: #00ff88;
            --dark-bg: #0a0e27;
            --card-bg: #1a1f3a;
            --text-light: #e0e0e0;
            --text-muted: #888;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
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
            font-size: 2.2em;
            color: var(--primary);
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
            margin-bottom: 10px;
        }
        .nav {
            text-align: center;
            margin-bottom: 30px;
        }
        .nav a {
            color: var(--primary);
            text-decoration: none;
            padding: 10px 20px;
            border: 1px solid var(--primary);
            border-radius: 5px;
            margin: 0 10px;
            display: inline-block;
            transition: all 0.3s;
            cursor: pointer;
        }
        .nav a:hover {
            background: var(--primary);
            color: #000;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-box {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid var(--primary);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .stat-value {
            font-size: 28px;
            color: var(--success);
            font-weight: bold;
        }
        .stat-label {
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 5px;
        }
        .blocks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .block-card {
            background: var(--card-bg);
            border: 2px solid var(--primary);
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
        }
        .block-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
            border-color: var(--success);
        }
        .block-header {
            font-size: 1.1em;
            color: var(--success);
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--primary);
            padding-bottom: 10px;
        }
        .block-preview {
            color: var(--text-muted);
            font-size: 0.85em;
            margin: 5px 0;
        }
        .hash-preview {
            color: var(--primary);
            font-size: 0.7em;
            word-break: break-all;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--primary);
            font-family: monospace;
            background: rgba(0, 212, 255, 0.1);
            padding: 5px;
            border-radius: 3px;
        }
        .hash-link {
            color: var(--success);
            font-size: 0.65em;
            margin-top: 3px;
            font-family: monospace;
        }
        .threat-badge {
            display: inline-block;
            background: rgba(255, 51, 51, 0.2);
            border: 1px solid var(--danger);
            color: var(--danger);
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            margin-top: 5px;
        }
        .threat-badge.high {
            background: rgba(255, 165, 0, 0.2);
            border-color: var(--warning);
            color: var(--warning);
        }
        .threat-badge.success {
            background: rgba(0, 255, 136, 0.2);
            border-color: var(--success);
            color: var(--success);
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            overflow-y: auto;
        }
        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .modal-content {
            background: var(--card-bg);
            border: 2px solid var(--primary);
            border-radius: 10px;
            padding: 30px;
            max-width: 900px;
            width: 95%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        }
        .close-btn {
            position: absolute;
            top: 15px;
            right: 20px;
            background: var(--danger);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1.2em;
        }
        .close-btn:hover {
            background: #cc0000;
        }
        .modal-header {
            color: var(--primary);
            font-size: 1.5em;
            margin-bottom: 20px;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 15px;
        }
        .modal-body {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .image-section {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .image-section img {
            max-width: 100%;
            border: 2px solid var(--primary);
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .image-label {
            color: var(--text-muted);
            font-size: 0.9em;
            text-align: center;
        }
        .images-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .details-section {
            display: flex;
            flex-direction: column;
            grid-column: 2;
        }
        .detail-item {
            background: rgba(0, 212, 255, 0.1);
            padding: 12px;
            border-left: 3px solid var(--primary);
            margin-bottom: 10px;
            border-radius: 4px;
        }
        .detail-label {
            color: var(--primary);
            font-weight: bold;
            font-size: 0.9em;
        }
        .detail-value {
            color: var(--text-light);
            margin-top: 4px;
        }
        .threats-list {
            margin-top: 20px;
        }
        .threats-list h3 {
            color: var(--primary);
            margin-bottom: 10px;
            border-bottom: 1px solid var(--primary);
            padding-bottom: 10px;
        }
        .threat-item {
            background: rgba(255, 51, 51, 0.1);
            border-left: 3px solid var(--danger);
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
        }
        .threat-item.high {
            border-left-color: var(--warning);
            background: rgba(255, 165, 0, 0.1);
        }
        .threat-item.medium {
            border-left-color: var(--success);
            background: rgba(0, 255, 136, 0.1);
        }
        .threat-name {
            font-weight: bold;
            color: var(--text-light);
        }
        .threat-severity {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-left: 8px;
        }
        .threat-severity.critical {
            background: var(--danger);
            color: white;
        }
        .threat-severity.high {
            background: var(--warning);
            color: #000;
        }
        .threat-severity.medium {
            background: var(--success);
            color: #000;
        }
        .threat-confidence {
            color: var(--text-muted);
            font-size: 0.85em;
            margin-top: 4px;
        }
        @media (max-width: 768px) {
            .modal-body {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⛓ Blockchain Ledger</h1>
            <p style="color: var(--text-muted);">Immutable record of all X-RAY scans</p>
        </header>

        <div class="nav">
            <a href="/">← Back to Scanner</a>
        </div>

        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">""" + str(len(blockchain.chain)) + """</div>
                <div class="stat-label">Total Blocks</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">""" + str(len(blockchain.chain) - 1) + """</div>
                <div class="stat-label">Scans Recorded</div>
            </div>
        </div>

        <div class="blocks-grid" id="blocksGrid"></div>
    </div>

    <!-- Detail Modal -->
    <div class="modal" id="detailModal">
        <div class="modal-content">
            <button class="close-btn" onclick="closeModal()">✕</button>
            <div class="modal-header" id="modalHeader"></div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        const blocks = """ + json.dumps([{
            'index': b.index,
            'timestamp': b.timestamp,
            'hash': b.hash,
            'previous_hash': b.previous_hash,
            'data': b.data if isinstance(b.data, dict) else {}
        } for b in blockchain.chain]) + """;

        function generateBlocks() {
            const grid = document.getElementById('blocksGrid');
            blocks.forEach(block => {
                const data = block.data || {};
                const detections = data.detections || [];
                const threats = detections.filter(d => d.severity && d.severity !== 'INFO');
                
                const card = document.createElement('div');
                card.className = 'block-card';
                card.onclick = () => showDetails(block);

                let content = `<div class="block-header">Block #${block.index}</div>`;
                
                if (data.filename) {
                    content += `<div class="block-preview"><strong>File:</strong> ${data.filename.substring(0, 30)}</div>`;
                }
                
                if (data.timestamp) {
                    const date = new Date(data.timestamp).toLocaleString();
                    content += `<div class="block-preview"><strong>Time:</strong> ${date}</div>`;
                }
                
                if (threats.length > 0) {
                    content += `<div class="threat-badge">🚨 ${threats.length} Threat(s)</div>`;
                } else {
                    content += `<div class="threat-badge success">✓ Safe - No Threats</div>`;
                }

                content += `<div class="hash-preview">Hash: ${block.hash.substring(0, 16)}...</div>`;
                
                if (block.index > 0) {
                    content += `<div class="hash-link">← Previous: ${block.previous_hash.substring(0, 16)}...</div>`;
                }

                card.innerHTML = content;
                grid.appendChild(card);
            });
        }

        function showDetails(block) {
            const data = block.data || {};
            const detections = data.detections || [];
            
            const header = document.getElementById('modalHeader');
            header.innerHTML = `Block #${block.index} - ${data.filename || 'Scan'}`;

            const body = document.getElementById('modalBody');
            
            let imageHtml = `<div class="images-container">`;
            
            if (data.original_image) {
                imageHtml += `
                    <div class="image-section">
                        <h3 style="color: var(--primary); margin-bottom: 10px; text-align: center;">Scanned Image</h3>
                        <img src="data:image/jpeg;base64,${data.original_image}" alt="Original">
                        <div class="image-label">Original Image</div>
                    </div>
                `;
            }

            if (data.annotated_image) {
                imageHtml += `
                    <div class="image-section">
                        <h3 style="color: var(--success); margin-bottom: 10px; text-align: center;">Annotated Image</h3>
                        <img src="data:image/jpeg;base64,${data.annotated_image}" alt="Annotated">
                        <div class="image-label">Analysis Result</div>
                    </div>
                `;
            }

            imageHtml += `</div>`;

            let detailsHtml = `
                <div class="details-section">
                    <div class="detail-item">
                        <div class="detail-label">🔗 Block Hash</div>
                        <div class="detail-value" style="font-family: monospace; font-size: 0.8em; word-break: break-all;">${block.hash}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">🔐 Previous Hash</div>
                        <div class="detail-value" style="font-family: monospace; font-size: 0.8em; word-break: break-all;">${block.previous_hash}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Timestamp</div>
                        <div class="detail-value">${data.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Filename</div>
                        <div class="detail-value">${data.filename || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Total Threats Detected</div>
                        <div class="detail-value">${data.total_threats || 0}</div>
                    </div>
            `;

            if (detections.length > 0) {
                detailsHtml += `
                    <div class="threats-list">
                        <h3>Threat Details</h3>
                `;
                
                detections.forEach(det => {
                    const severity = det.severity || 'UNKNOWN';
                    const severityClass = severity === 'CRITICAL' ? 'critical' : severity === 'HIGH' ? 'high' : 'medium';
                    const confidence = (det.confidence * 100).toFixed(1);
                    
                    detailsHtml += `
                        <div class="threat-item ${severity.toLowerCase()}">
                            <div class="threat-name">
                                🚨 ${det.item}
                                <span class="threat-severity ${severityClass}">${severity}</span>
                            </div>
                            <div class="threat-confidence">Confidence: ${confidence}%</div>
                        </div>
                    `;
                });

                detailsHtml += `</div>`;
            } else {
                detailsHtml += `<div class="detail-item"><strong style="color: var(--success);">✓ No threats detected - Image is SAFE</strong></div>`;
            }

            detailsHtml += `</div>`;

            body.innerHTML = imageHtml + detailsHtml;
            document.getElementById('detailModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('detailModal').classList.remove('active');
        }

        document.getElementById('detailModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });

        generateBlocks();
    </script>
</body>
</html>"""
    return html


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
