import torch
import numpy as np
import cv2

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

class EnhancedVehicleDetector:
    def __init__(self):
        self.model = None
        self.vehicle_classes = ['auto', 'bike', 'bus', 'car', 'emergency_vehicles', 'truck']
        self.vehicle_weights = {
            'auto': 0.8,
            'bike': 0.5,
            'bus': 2.0,
            'car': 1.0,
            'emergency_vehicles': 1.5,
            'truck': 2.5
        }
        self.new_vehicle_classes = {
            0: 'auto',
            1: 'bike',
            2: 'bus',
            3: 'car',
            4: 'emergency_vehicles',
            5: 'truck'
        }
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")

        # Performance optimization settings
        self.frame_skip = 2  # Process every 2nd frame
        self.frame_counter = 0
        self.input_size = (640, 640)  # Standard YOLO input size
        self.last_detection_time = 0
        self.avg_inference_time = 0

        self.load_yolo_model()

    def load_yolo_model(self):
        try:
            if YOLO_AVAILABLE:
                try:
                    self.model = YOLO(r"C:\Users\anime\PycharmProjects\PythonProject4\traffic_system\my_model (2).pt")
                    self.model.to(self.device)
                    print("✅ YOLOv8 model loaded successfully")
                    return True
                except Exception as e:
                    print(f"Error loading YOLOv8 model: {e}")
                    return False
            else:
                print("YOLOv8 not available. Using simulated detection.")
                return False
        except Exception as e:
            print(f"Error in YOLO initialization: {e}")
            print("Falling back to simulated detection")
            self.model = None
            return False

    def detect_vehicles_in_area(self, frame, area_points, draw_area=True):
        if frame is None:
            return 0, 0, None, {k: 0 for k in self.vehicle_classes}, 0.0

        try:
            # Create mask for the defined area
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            area_points_np = np.array(area_points, dtype=np.int32)
            cv2.fillPoly(mask, [area_points_np], 255)

            # Create a copy of the frame for visualization
            processed_frame = frame.copy()

            # Draw detection area only if requested
            if draw_area:
                cv2.polylines(processed_frame, [area_points_np], True, (0, 255, 255), 3)
                cv2.putText(processed_frame, "Detection Area",
                            (area_points_np[0][0], area_points_np[0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Initialize vehicle counts
            vehicle_counts = {k: 0 for k in self.vehicle_classes}

            # Detect vehicles using YOLOv8
            if self.model is not None:
                try:
                    # Preprocess frame
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Run inference with optimized parameters
                    results = self.model(
                        frame_rgb,
                        conf=0.25,
                        iou=0.45,
                        max_det=50,
                        classes=[0, 1, 2, 3, 4, 5],
                        verbose=False
                    )

                    vehicle_count = 0
                    traffic_weight = 0
                    detected_centers = []
                    confidences = []

                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                # Get box coordinates
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                x, y = int((x1 + x2) / 2), int((y1 + y2) / 2)  # center point

                                # Check if center point is in the detection area
                                if self.point_in_polygon((x, y), area_points):
                                    # Check if we already detected a vehicle at this location
                                    too_close = False
                                    for cx, cy in detected_centers:
                                        if abs(x - cx) < 30 and abs(y - cy) < 30:  # 30 pixel threshold
                                            too_close = True
                                            break

                                    if not too_close:
                                        detected_centers.append((x, y))
                                        class_id = int(box.cls[0].cpu().numpy())
                                        confidence = float(box.conf[0].cpu().numpy())
                                        confidences.append(confidence)

                                        if class_id in self.new_vehicle_classes:
                                            vehicle_count += 1
                                            class_name = self.new_vehicle_classes[class_id]
                                            traffic_weight += self.vehicle_weights.get(class_name, 1.0)
                                            vehicle_counts[class_name] += 1

                                            # Draw bounding box with different colors based on vehicle type
                                            color = {
                                                'auto': (128, 128, 128),
                                                'bike': (0, 255, 255),
                                                'bus': (255, 165, 0),
                                                'car': (0, 255, 0),
                                                'emergency_vehicles': (255, 0, 0),
                                                'truck': (255, 0, 0)
                                            }.get(class_name, (0, 255, 0))

                                            # Draw bounding box and label
                                            cv2.rectangle(processed_frame,
                                                          (int(x1), int(y1)),
                                                          (int(x2), int(y2)),
                                                          color, 2)

                                            # Add background to text for better visibility
                                            label = f"{class_name}: {confidence:.2f}"
                                            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                                            cv2.rectangle(processed_frame,
                                                          (int(x1), int(y1 - 20)),
                                                          (int(x1 + label_w), int(y1)),
                                                          color, -1)
                                            cv2.putText(processed_frame, label,
                                                        (int(x1), int(y1 - 5)),
                                                        cv2.FONT_HERSHEY_SIMPLEX,
                                                        0.5, (255, 255, 255), 2)

                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                    # Add detection info with background
                    info_bg_color = (0, 0, 0)
                    info_text_color = (255, 255, 255)

                    # Vehicle count background
                    cv2.rectangle(processed_frame, (10, 10), (150, 35), info_bg_color, -1)
                    cv2.putText(processed_frame, f"Vehicles: {vehicle_count}",
                                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, info_text_color, 2)

                    # Traffic weight background
                    cv2.rectangle(processed_frame, (10, 40), (200, 65), info_bg_color, -1)
                    cv2.putText(processed_frame, f"Traffic Weight: {traffic_weight:.1f}",
                                (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, info_text_color, 2)

                    return vehicle_count, traffic_weight, processed_frame, vehicle_counts, avg_confidence

                except Exception as e:
                    print(f"YOLO detection error: {str(e)}")
                    return self.simulate_detection(frame, mask)
            else:
                return self.simulate_detection(frame, mask)

        except Exception as e:
            print(f"Error in vehicle detection: {e}")
            return 0, 0, frame, {k: 0 for k in self.vehicle_classes}, 0.0

    def simulate_detection(self, frame, mask):
        """Simulate vehicle detection when YOLO is not available"""
        vehicle_type_counts = {k: 0 for k in self.vehicle_classes}

        # Create a copy of frame for visualization
        processed_frame = frame.copy()

        # Simulate random detections
        height, width = frame.shape[:2]
        num_vehicles = np.random.randint(1, 12)
        total_weight = 0
        confidences = []

        for _ in range(num_vehicles):
            x = np.random.randint(0, width - 100)
            y = np.random.randint(0, height - 60)
            w = np.random.randint(80, 120)
            h = np.random.randint(40, 80)
            class_name = np.random.choice(self.vehicle_classes)
            confidence = np.random.uniform(0.5, 0.95)
            confidences.append(confidence)

            # Update vehicle type count
            vehicle_type_counts[class_name] += 1

            # Add to total weight
            total_weight += self.vehicle_weights.get(class_name, 1.0)

            # Draw bounding box with different colors based on vehicle type
            color = {
                'auto': (128, 128, 128),      # Gray
                'bike': (0, 255, 255),        # Yellow
                'bus': (255, 165, 0),         # Orange
                'car': (0, 255, 0),           # Green
                'emergency_vehicles': (255, 0, 0),  # Red
                'truck': (255, 0, 0)          # Red
            }.get(class_name, (0, 255, 0))

            # Draw rectangle and label
            cv2.rectangle(processed_frame, (x, y), (x + w, y + h), color, 2)
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(processed_frame, label, (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return num_vehicles, total_weight, processed_frame, vehicle_type_counts, avg_confidence

    def point_in_polygon(self, point, polygon):
        x, y = point
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside