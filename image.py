from pathlib import Path
import numpy as np
import cv2
import base64
import io

__all__ = ["detect_threats", "apply_xray_effect", "verify_progress", "get_xray_frame"]

# Import YOLO for real object detection
try:
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not available. Using fallback detection.")

# Global YOLO model (loaded once for performance)
yolo_model = None

# Threat/Dangerous object classes to detect
THREAT_CLASSES = {
    "knife": {"severity": "HIGH", "color": (0, 165, 255)},  # Orange in BGR
    "gun": {"severity": "CRITICAL", "color": (0, 0, 255)},  # Red
    "pistol": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "rifle": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "bomb": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "backpack": {"severity": "INFO", "color": (0, 255, 255)},  # Cyan
    "person": {"severity": "INFO", "color": (255, 0, 0)},  # Blue
    "handbag": {"severity": "INFO", "color": (0, 255, 255)},
    "bag": {"severity": "INFO", "color": (0, 255, 255)},
    "bottle": {"severity": "LOW", "color": (0, 255, 100)},  # Green
}

def load_yolo_model():
    """Load YOLOv8 model for object detection"""
    global yolo_model
    if not YOLO_AVAILABLE:
        return None
    
    try:
        if yolo_model is None:
            from ultralytics import YOLO
            # Use YOLOv8 small model (faster inference)
            yolo_model = YOLO('yolov8s.pt')  # Small model
            print("✓ YOLOv8 model loaded successfully")
        return yolo_model
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        return None

def apply_xray_effect(frame):
    """
    Apply X-ray effect to create a "scanned" version of the image.
    Uses edge detection, contrast enhancement, and color mapping to simulate X-ray.
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for better contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply edge detection (Canny)
        edges = cv2.Canny(enhanced, 100, 200)
        
        # Apply morphological operations to enhance edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Create X-ray effect by inverted display
        xray = cv2.bitwise_not(edges)
        
        # Convert back to BGR for consistency
        xray_bgr = cv2.cvtColor(xray, cv2.COLOR_GRAY2BGR)
        
        # Add greenish tint like a real X-ray scanner
        xray_bgr[:,:,0] = cv2.multiply(xray_bgr[:,:,0], 0.3)  # Blue channel - reduce
        xray_bgr[:,:,1] = cv2.multiply(xray_bgr[:,:,1], 1.2)  # Green channel - enhance
        xray_bgr[:,:,2] = cv2.multiply(xray_bgr[:,:,2], 0.5)  # Red channel - reduce
        
        # Add some blur for authentic X-ray appearance
        xray_bgr = cv2.GaussianBlur(xray_bgr, (5, 5), 0)
        
        return xray_bgr
    except Exception as e:
        print(f"X-ray effect error: {e}")
        return frame

def apply_bag_see_through_effect(frame, detections):
    """
    Apply a special "see-through" effect to detected bags/containers.
    This simulates X-ray vision by enhancing contrast and revealing hidden objects.
    """
    try:
        enhanced_frame = frame.copy()
        
        # Find bag detections
        bag_detections = [d for d in detections if d.get("item", "").lower() in ["backpack", "handbag", "bag", "suitcase", "luggage"]]
        
        for bag in bag_detections:
            bbox = bag.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                
                # Ensure coordinates are within frame bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                
                if x2 > x1 and y2 > y1:
                    # Extract bag region
                    bag_roi = frame[y1:y2, x1:x2].copy()
                    
                    # Apply see-through effect to bag region
                    see_through_roi = apply_see_through_filter(bag_roi)
                    
                    # Blend the see-through effect with original
                    alpha = 0.7  # Transparency level
                    enhanced_frame[y1:y2, x1:x2] = cv2.addWeighted(
                        bag_roi, 1 - alpha, 
                        see_through_roi, alpha, 
                        0
                    )
                    
                    # Add "X-RAY VISION" text overlay
                    cv2.putText(enhanced_frame, "X-RAY VISION", (x1 + 10, y1 + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return enhanced_frame
        
    except Exception as e:
        print(f"Bag see-through effect error: {e}")
        return frame

def apply_see_through_filter(roi):
    """
    Apply a filter that simulates seeing through bags by enhancing edges and contrast.
    """
    try:
        # Convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Enhance contrast in L channel
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Merge back
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Apply edge enhancement
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate edges to make them more visible
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Create green overlay for "X-ray" effect
        green_overlay = np.zeros_like(roi)
        green_overlay[:, :, 1] = edges_dilated  # Green channel
        
        # Blend original enhanced image with green overlay
        result = cv2.addWeighted(enhanced, 0.8, green_overlay, 0.4, 0)
        
        return result
        
    except Exception as e:
        print(f"See-through filter error: {e}")
        return roi

def detect_threats(image_path):
    """
    Real object detection using YOLOv8.
    Returns list of detected threats with location, confidence, and severity.
    """
    try:
        # Load the original image
        frame = cv2.imread(image_path)
        if frame is None:
            return {"detections": [], "xray_image": None}
        
        return detect_threats_from_frame(frame, image_path)
    
    except Exception as e:
        print(f"Detection error: {e}")
        return {"detections": [], "xray_image": None}

def detect_threats_from_frame(frame, image_id="temp"):
    """
    Detect threats in a frame using YOLOv8.
    Real detection with bounding boxes and threat classification.
    """
    detections = []
    annotated_frame = frame.copy()
    
    try:
        model = load_yolo_model()
        
        if model is not None:
            # Run YOLO detection
            results = model(frame, conf=0.4, verbose=False)
            
            # Process results
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Get class name and confidence
                    class_name = result.names[int(box.cls[0])]
                    confidence = float(box.conf[0])
                    
                    # Check if this is a threat/suspicious item
                    is_threat = False
                    severity = "INFO"
                    color = (100, 100, 100)
                    
                    # Check if it's a dangerous item
                    class_lower = class_name.lower()
                    if any(threat in class_lower for threat in ["knife", "gun", "pistol", "rifle", "bomb", "weapon", "scissors", "axe", "sword", "baton"]):
                        is_threat = True
                        if any(critical in class_lower for critical in ["gun", "pistol", "rifle", "bomb", "explosive"]):
                            severity = "CRITICAL"
                            color = (0, 0, 255)  # Red
                        else:
                            severity = "HIGH"
                            color = (0, 165, 255)  # Orange
                    elif any(suspicious in class_lower for suspicious in ["backpack", "handbag", "bag", "suitcase", "luggage"]):
                        # Bags are suspicious (could contain items)
                        is_threat = True
                        severity = "SCANNING"
                        color = (0, 255, 255)  # Cyan
                    elif any(chemical in class_lower for chemical in ["bottle", "can", "container", "flask"]):
                        # Containers could hold dangerous liquids
                        is_threat = True
                        severity = "WARNING"
                        color = (0, 255, 100)  # Green
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Add label
                    label = f"{class_name}: {confidence:.2f}"
                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    # Add to detections if threat
                    if is_threat or severity == "SCANNING":
                        detections.append({
                            "item": class_name,
                            "severity": severity,
                            "confidence": round(confidence, 3),
                            "bbox": [x1, y1, x2, y2],
                            "color": f"#{color[2]:02x}{color[1]:02x}{color[0]:02x}",
                            "timestamp": __import__('datetime').datetime.now().isoformat()
                        })
        else:
            # Fallback: simple heuristic detection
            print("Using fallback detection mode")
            detections = fallback_detect_threats(frame)
    
    except Exception as e:
        print(f"YOLO detection error: {e}")
        detections = []
    
    # Apply bag see-through effect if bags are detected
    if detections:
        bag_detections = [d for d in detections if d.get("item", "").lower() in ["backpack", "handbag", "bag", "suitcase", "luggage"]]
        if bag_detections:
            annotated_frame = apply_bag_see_through_effect(annotated_frame, detections)
    
    return {
        "detections": detections,
        "annotated_frame": annotated_frame
    }

def fallback_detect_threats(frame):
    """
    Fallback detection using color and shape analysis.
    Used when YOLO is not available.
    """
    detections = []
    
    try:
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Detect dark metallic objects (potential weapons)
        lower_dark = np.array([0, 0, 0])
        upper_dark = np.array([180, 255, 50])
        dark_mask = cv2.inRange(hsv, lower_dark, upper_dark)
        
        # Detect bright/reflective objects (potential metallic items)
        lower_bright = np.array([0, 0, 200])
        upper_bright = np.array([180, 30, 255])
        bright_mask = cv2.inRange(hsv, lower_bright, upper_bright)
        
        # Combine masks
        combined_mask = cv2.bitwise_or(dark_mask, bright_mask)
        
        # Apply morphological operations to clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze contours for threat-like shapes
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 300:  # Minimum size threshold
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check aspect ratio (weapons are often elongated)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # Calculate compactness (weapons tend to be more compact)
                perimeter = cv2.arcLength(contour, True)
                compactness = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                threat_level = "LOW"
                confidence = 0.4
                
                if 0.1 < aspect_ratio < 10:  # Elongated shapes like weapons
                    if compactness > 0.3:  # Compact shape
                        threat_level = "HIGH"
                        confidence = 0.75
                    else:
                        threat_level = "MEDIUM"
                        confidence = 0.6
                
                detections.append({
                    "item": "Suspicious Metallic Object",
                    "severity": threat_level,
                    "confidence": confidence,
                    "bbox": [x, y, x + w, y + h],
                    "color": "#FF6600",
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
    
    except Exception as e:
        print(f"Fallback detection error: {e}")
    
    return detections

def get_xray_frame(frame):
    """
    Get X-ray processed version of frame and return as base64.
    """
    try:
        xray = apply_xray_effect(frame)
        
        # Encode to base64 for transmission
        _, buffer = cv2.imencode('.jpg', xray)
        xray_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return xray_base64
    except Exception as e:
        print(f"X-ray frame error: {e}")
        return None

def verify_progress(before_path, after_path, threshold=0.08):
    """
    Verify visual progress between two images.
    Returns a dict with verdict, score, and details.
    """
    b = Path(before_path)
    a = Path(after_path)

    if not b.exists() or not a.exists():
        return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": "file missing"}

    try:
        from PIL import Image
    except Exception:
        # Fallback: use file size heuristic
        try:
            s1 = b.stat().st_size
            s2 = a.stat().st_size
            if max(s1, s2) == 0:
                score = 0.0
            else:
                score = abs(s2 - s1) / max(s1, s2)
            verdict = score >= threshold
            return {"verdict": verdict, "score": float(score), "threshold": threshold, "detail": "filesize-heuristic"}
        except Exception as e:
            return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": f"fallback-failed: {e}"}

    try:
        # Open images and compare
        im1 = Image.open(str(b)).convert("L").resize((64, 64), Image.LANCZOS)
        im2 = Image.open(str(a)).convert("L").resize((64, 64), Image.LANCZOS)

        p1 = list(im1.getdata())
        p2 = list(im2.getdata())

        # Compute normalized mean absolute difference
        total_pixels = len(p1)
        if total_pixels == 0:
            score = 0.0
        else:
            score = sum(abs(p1[i] - p2[i]) for i in range(total_pixels)) / (255.0 * total_pixels)
        
        verdict = score >= threshold
        return {"verdict": verdict, "score": float(score), "threshold": threshold, "detail": "pixel-diff"}
    
    except Exception as e:
        return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": f"error: {str(e)}"}
