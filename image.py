from pathlib import Path
import numpy as np
import cv2
import base64
import io

__all__ = ["detect_threats", "apply_xray_effect", "verify_progress", "get_xray_frame", "generate_explainable_annotation"]

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception as e:
    YOLO_AVAILABLE = False
    YOLO = None
    print(f"Warning: YOLO not available ({type(e).__name__}). Using fallback detection.")

yolo_model = None

THREAT_CLASSES = {
    "knife": {"severity": "HIGH", "color": (0, 165, 255)},
    "gun": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "pistol": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "rifle": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "bomb": {"severity": "CRITICAL", "color": (0, 0, 255)},
    "backpack": {"severity": "INFO", "color": (0, 255, 255)},
    "person": {"severity": "INFO", "color": (255, 0, 0)},
    "handbag": {"severity": "INFO", "color": (0, 255, 255)},
    "bag": {"severity": "INFO", "color": (0, 255, 255)},
    "bottle": {"severity": "LOW", "color": (0, 255, 100)},
}


def load_yolo_model():
    global yolo_model
    if not YOLO_AVAILABLE:
        return None

    try:
        if yolo_model is None:
            yolo_model = YOLO('yolov8s.pt')
            print("✓ YOLOv8 model loaded successfully")
        return yolo_model
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        return None


def apply_xray_effect(frame):
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        edges = cv2.Canny(enhanced, 100, 200)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        xray = cv2.bitwise_not(edges)
        xray_bgr = cv2.cvtColor(xray, cv2.COLOR_GRAY2BGR)
        xray_bgr[:,:,0] = cv2.multiply(xray_bgr[:,:,0], 0.3)
        xray_bgr[:,:,1] = cv2.multiply(xray_bgr[:,:,1], 1.2)
        xray_bgr[:,:,2] = cv2.multiply(xray_bgr[:,:,2], 0.5)
        xray_bgr = cv2.GaussianBlur(xray_bgr, (5, 5), 0)
        return xray_bgr
    except Exception as e:
        print(f"X-ray effect error: {e}")
        return frame


def apply_bag_see_through_effect(frame, detections):
    try:
        enhanced_frame = frame.copy()
        bag_detections = [d for d in detections if d.get("item", "").lower() in ["backpack", "handbag", "bag", "suitcase", "luggage"]]
        for bag in bag_detections:
            bbox = bag.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                if x2 > x1 and y2 > y1:
                    bag_roi = frame[y1:y2, x1:x2].copy()
                    see_through_roi = apply_see_through_filter(bag_roi)
                    alpha = 0.7
                    enhanced_frame[y1:y2, x1:x2] = cv2.addWeighted(
                        bag_roi, 1 - alpha,
                        see_through_roi, alpha,
                        0
                    )
                    cv2.putText(enhanced_frame, "X-RAY VISION", (x1 + 10, y1 + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return enhanced_frame
    except Exception as e:
        print(f"Bag see-through effect error: {e}")
        return frame


def apply_see_through_filter(roi):
    try:
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        green_overlay = np.zeros_like(roi)
        green_overlay[:, :, 1] = edges_dilated
        result = cv2.addWeighted(enhanced, 0.8, green_overlay, 0.4, 0)
        return result
    except Exception as e:
        print(f"See-through filter error: {e}")
        return roi


def detect_threats(image_path):
    try:
        frame = cv2.imread(image_path)
        if frame is None:
            return {"detections": [], "xray_image": None}
        return detect_threats_from_frame(frame, image_path)
    except Exception as e:
        print(f"Detection error: {e}")
        return {"detections": [], "xray_image": None}


def detect_threats_from_frame(frame, image_id="temp"):
    detections = []
    annotated_frame = frame.copy()
    try:
        model = load_yolo_model()
        if model is not None:
            results = model(frame, conf=0.4, verbose=False)
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    class_name = result.names[int(box.cls[0])]
                    confidence = float(box.conf[0])
                    is_threat = False
                    severity = "INFO"
                    color = (100, 100, 100)
                    class_lower = class_name.lower()
                    if any(threat in class_lower for threat in ["knife", "gun", "pistol", "rifle", "bomb", "weapon", "scissors", "axe", "sword", "baton"]):
                        is_threat = True
                        if any(critical in class_lower for critical in ["gun", "pistol", "rifle", "bomb", "explosive"]):
                            severity = "CRITICAL"
                            color = (0, 0, 255)
                        else:
                            severity = "HIGH"
                            color = (0, 165, 255)
                    elif any(suspicious in class_lower for suspicious in ["backpack", "handbag", "bag", "suitcase", "luggage"]):
                        is_threat = True
                        severity = "SCANNING"
                        color = (0, 255, 255)
                    elif any(chemical in class_lower for chemical in ["bottle", "can", "container", "flask"]):
                        is_threat = True
                        severity = "WARNING"
                        color = (0, 255, 100)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{class_name}: {confidence:.2f}"
                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
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
            # Fallback detection when YOLO isn't available
            h, w = frame.shape[:2]
            detections = [{
                "item": "unknown",
                "severity": "INFO",
                "confidence": 0.0,
                "bbox": [int(w*0.25), int(h*0.25), int(w*0.75), int(h*0.75)],
                "color": "#00ff00",
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }]
        return {"detections": detections, "annotated_frame": annotated_frame}
    except Exception as e:
        print(f"Detection error: {e}")
        return {"detections": [], "annotated_frame": None}
