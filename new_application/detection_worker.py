import os
import time
import cv2
import numpy as np
import json
import threading
from datetime import datetime
import django
from collections import deque
import redis

if __name__ == "__main__":
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_system.settings')
    django.setup()
    print("detection_worker.py: Django environment set up (running as main script).")
else:
    pass

import django.conf
from django.conf import settings
from .models import TrafficSignal, DetectionArea, VideoSource, TrafficLog, SystemSettings, CongestionEvent, TrafficData
from .detecter import EnhancedVehicleDetector

# Setup Redis connection (singleton)
redis_client = redis.StrictRedis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=getattr(settings, 'REDIS_DB', 0),
    decode_responses=False  # Use bytes for frames
)

class DetectionWorker:
    """Background worker for video processing and YOLO detection"""
    
    def __init__(self):
        self.detector = EnhancedVehicleDetector()
        self.video_caps = [None] * 4
        self.current_frames = [None] * 4
        self.running = False
        self.detection_thread = None

         # Setup Redis PubSub for control messages
        self.redis_control_pubsub = redis_client.pubsub() # Add this line
        self.CONTROL_CHANNEL = 'control_channel_detection_worker' 
        
        # Load system settings
        self.settings, _ = SystemSettings.objects.get_or_create(id=1)
        self.last_congestion_analysis_time = time.time()
        self.congestion_analysis_interval = 5.0

         # --- ADD THESE NEW ATTRIBUTES ---
        self.frame_counters = [0] * 4 # To track frames for each of the 4 signals
        self.frame_skip_count = 5 # Number of frames to skip (process 1, skip 2, process 1, ...)
                                  # Set to 0 to process every frame.
        
        # Initialize detection areas and video sources
        self.initialize_system()
    
    def initialize_system(self):
        """Initialize detection areas and video sources from database"""
        try:
            # Ensure all signals exist
            for i in range(4):
                signal, created = TrafficSignal.objects.get_or_create(
                    signal_id=i,
                    defaults={
                        'current_state': 'RED',
                        'min_green_time': 10,
                        'max_green_time': 45,
                        'default_green_time': 15,
                        'yellow_time': 3,
                        'all_red_time': 2,
                        'vehicle_type_counts': {
                            'auto': 0, 'bike': 0, 'bus': 0, 
                            'car': 0, 'emergency_vehicles': 0, 'truck': 0
                        }
                    }
                )
                
                DetectionArea.objects.get_or_create(
                    signal=signal,
                    defaults={
                        'area_points': [[100, 100], [200, 100], [200, 200], [100, 200]], # Default area for new signals
                        'area_size': 10000.0 # Default size
                    }
                )
                VideoSource.objects.get_or_create(
                    signal=signal,
                    defaults={
                        'video_path': '',
                        'is_active': False
                    }
                )
                
                if created:
                    print(f"Created new signal {chr(65+i)}")
            
            print("System initialization completed")
            
        except Exception as e:
            print(f"Error initializing system: {type(e)} - {e}")
    
    def initialize_video_captures(self):
        """Initialize OpenCV video captures for each signal"""
        # Inside DetectionWorker.initialize_video_captures
        for i in range(4):
            try:
                signal = TrafficSignal.objects.get(signal_id=i)
                video_source = signal.video_source

                print(f"Attempting to open video for Signal {chr(65+i)}: {video_source.video_path}")

                if video_source.is_active and os.path.exists(video_source.video_path):
                    self.video_caps[i] = cv2.VideoCapture(video_source.video_path)
                    if not self.video_caps[i].isOpened():
                        print(f"ERROR: Signal {chr(65+i)}: Failed to open video source: {video_source.video_path}")
                        # Try to get error code or reason if possible (OpenCV doesn't always give detailed errors here)
                        self.video_caps[i] = None
                    else:
                        self.video_caps[i].set(cv2.CAP_PROP_BUFFERSIZE, 2)
                        self.video_caps[i].set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        self.video_caps[i].set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        actual_width = int(self.video_caps[i].get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_height = int(self.video_caps[i].get(cv2.CAP_PROP_FRAME_HEIGHT))
                        # Only update if dimensions are different from what's stored or are 0
                        if video_source.width != actual_width or video_source.height != actual_height:
                            video_source.width = actual_width
                            video_source.height = actual_height
                            video_source.save(update_fields=['width', 'height']) # Save only these fields
                            print(f"Updated Signal {chr(65+i)} VideoSource dimensions to {actual_width}x{actual_height}")
                        else:
                            print(f"Signal {chr(65+i)} VideoSource dimensions already {actual_width}x{actual_height}.")

                        print(f"SUCCESS: Opened video for Signal {chr(65+i)} - Resolution set to {self.video_caps[i].get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.video_caps[i].get(cv2.CAP_PROP_FRAME_HEIGHT)}")
                        print(f"Signal {chr(65+i)}: Video properties: Frame Count={self.video_caps[i].get(cv2.CAP_PROP_FRAME_COUNT)}, FPS={self.video_caps[i].get(cv2.CAP_PROP_FPS)}")
                else:
                    print(f"WARNING: Video source not active or file does not exist for Signal {chr(65+i)}: {video_source.video_path} (exists: {os.path.exists(video_source.video_path)})")

            except Exception as e:
                print(f"CRITICAL ERROR during video capture initialization for Signal {chr(65+i)}: {type(e).__name__} - {e}")
    
    def _redis_control_listener_thread_func(self):
        print(f"DetectionWorker: Subscribing to Redis control channel: {self.CONTROL_CHANNEL}")
        self.redis_control_pubsub.subscribe(self.CONTROL_CHANNEL)
        
        for message in self.redis_control_pubsub.listen():
            if message['type'] == 'message':
                decoded_message = message['data'].decode('utf-8')
                print(f"DetectionWorker: Received control message: {decoded_message}")
                if decoded_message == 'reload_config':
                    self.reload_config_from_db()
    
    def capture_and_detect_frames(self):
        """Main detection loop - continuously captures frames and performs detection"""
        print("Starting frame capture and detection loop...")
        
        while self.running:
            try:
                for i in range(4):
                    cap = self.video_caps[i]
                    if cap and cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            print(f"Signal {chr(65+i)}: Successfully read frame. Shape: {frame.shape}, Dtype: {frame.dtype}")
                            self.current_frames[i] = frame.copy()
                            # Perform detection for this signal's area
                            if self.frame_counters[i] % (self.frame_skip_count + 1) == 0:
                                print(f"Signal {chr(65+i)}: PROCESSING frame {self.frame_counters[i]}.")
                                self.process_signal_detection(i, frame.copy())
                            else:
                                print(f"Signal {chr(65+i)}: SKIPPING frame {self.frame_counters[i]}.")
                        else:
                            # Loop video if end reache
                            print(f"Signal {chr(65+i)}: Read failed (ret={ret}, frame is None={frame is None}). Attempting to loop video.")
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = cap.read() # Try reading again after seeking
                            if ret and frame is not None:
                                print(f"Signal {chr(65+i)}: Successfully read frame after loop. Shape: {frame.shape}")
                                self.current_frames[i] = frame.copy()
                                self.process_signal_detection(i, frame.copy())
                            else:
                                print(f"ERROR: Signal {chr(65+i)}: Still failed to read frame after looping. Cap status: {cap.isOpened()}")
                    else:
                        # Try to reinitialize if capture is not open
                        if self.running:
                            self.reinitialize_video_capture(i)
                
                # Sleep based on detection interval setting
                time.sleep(self.settings.detection_interval)
                
            except Exception as e:
                print(f"Error in detection loop: {e}")
                time.sleep(1.0)  # Wait longer on error
    # calculating congestion levels
    def calculate_congestion_level(self, vehicle_count, traffic_weight, area_size):
        if area_size <= 0:
            area_size = 1000 # Default area size to prevent division by zero

        density = vehicle_count / area_size
        weighted_density = traffic_weight / area_size
        
        if area_size > 50000: # Adjust threshold as needed
            congestion_score = (density * 10000) + (vehicle_count * 0.5) + (weighted_density * 0.3)
        else:
            congestion_score = (density * 0.3 + weighted_density * 0.7) * 1000
        
        if congestion_score < 2:
            congestion_level = 'LOW'
            color = 'green'
        elif congestion_score < 8:
            congestion_level = 'MODERATE'
            color = 'orange'
        elif congestion_score < 20:
            congestion_level = 'HIGH'
            color = 'red'
        else:
            congestion_level = 'SEVERE'
            color = 'darkred'
        
        return congestion_level, congestion_score, color

    
    def process_signal_detection(self, signal_idx, frame):
        """Process detection for a specific signal"""
        try:
            signal_char = chr(65 + signal_idx)
            print(f"--- Signal {signal_char}: Starting process_signal_detection ---")
            signal = TrafficSignal.objects.get(signal_id=signal_idx)
            detection_area = signal.detection_area
            
            if not detection_area.area_points:
                print(f"WARNING: Signal {signal_char}: No detection area points defined. Skipping detection.")
                return
            
            # Run YOLO detection
            vehicle_count, traffic_weight, processed_frame, vehicle_type_counts, avg_confidence = \
                self.detector.detect_vehicles_in_area(frame, detection_area.area_points, draw_area=True)
            
            print(f"Signal {chr(65+signal_idx)}: Raw Detection Output - Count={vehicle_count}, Weight={traffic_weight}, Types={vehicle_type_counts}")
            
            # Update signal data in database
            signal.vehicle_count = vehicle_count
            signal.traffic_weight = traffic_weight
            signal.vehicle_type_counts = vehicle_type_counts
            signal.avg_confidence = avg_confidence
            signal.last_update_time = datetime.now()
            
            # Check for emergency vehicles
            emergency_count = vehicle_type_counts.get('emergency_vehicles', 0)
            if emergency_count > 0:
                signal.has_emergency_vehicle = True
                signal.emergency_vehicle_detected_time = datetime.now()
                signal.emergency_vehicle_wait_time = 0.0
            else:
                signal.has_emergency_vehicle = False
            
            signal.save()

            #------------***THIS IS THE Addition of TrafficData***------------#
            TrafficData.objects.create( # <--- This is a CREATE NEW RECORD operation for TrafficDataSnapshot
                signal=signal,
                vehicle_count=vehicle_count,
                traffic_weight=traffic_weight,
                green_time=signal.calculated_green_time,
                auto_count=vehicle_type_counts.get('auto', 0),
                bike_count=vehicle_type_counts.get('bike', 0),
                bus_count=vehicle_type_counts.get('bus', 0),
                car_count=vehicle_type_counts.get('car', 0),
                emergency_vehicles_count=vehicle_type_counts.get('emergency_vehicles', 0),
                truck_count=vehicle_type_counts.get('truck', 0),
                vehicle_type_counts_json=vehicle_type_counts
            )

            # --- CONGESTION ANALYSIS INTEGRATION (Calculated periodically, creates CongestionEvent) ---#
            current_time = time.time()
            if current_time - self.last_congestion_analysis_time >= self.congestion_analysis_interval:
                self.last_congestion_analysis_time = current_time # Reset timer for next analysis
                print(f"Performing congestion analysis for Signal {signal_char}...")
                
                # Get area_size from the detection_area object
                area_size_for_analysis = detection_area.area_size 
                if area_size_for_analysis is None or area_size_for_analysis <= 0:
                    area_size_for_analysis = 1000 # Fallback default

                congestion_level, congestion_score, color = self.calculate_congestion_level(
                    signal.vehicle_count, # Use latest total_vehicle_count
                    signal.traffic_weight,     # Use latest traffic_weight
                    area_size_for_analysis
                )

                # Update the TrafficSignal's congestion_level and congestion_score fields
                signal.update_congestion_data(congestion_level, congestion_score)

                CongestionEvent.objects.create(
                    signal=signal,
                    severity=congestion_level, # Map to 'severity' field
                    score=congestion_score,
                    color=color,
                    cause="High traffic density detected by AI", # Default cause
                    resolution_time=None # No resolution logic yet
                )
            print(f"CongestionEvent created for Signal {signal_char}.")
            #------------Congestion_Analysis_Ends here--------------------------------------------------#
            
            # Log detection update
            TrafficLog.objects.create(
                signal=signal,
                event_type='DETECTION_UPDATE',
                details={
                    'vehicle_count': vehicle_count,
                    'traffic_weight': traffic_weight,
                    'vehicle_type_counts': vehicle_type_counts,
                    'avg_confidence': avg_confidence
                }
            )
            # Store processed frame for MJPEG streaming
            if processed_frame is not None:
                print(f"Signal {chr(65+signal_idx)}: Processed Frame Shape: {processed_frame.shape}")
                if processed_frame.size > 0 and processed_frame.ndim >= 2:
                    success, buffer = cv2.imencode('.jpg', processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                    if success and buffer is not None:
                        frame_bytes = buffer.tobytes()
                        # Publish to Redis channel
                        channel = f'frame_channel_{signal_idx}'
                        redis_client.publish(channel, frame_bytes)
                        print(f"Signal {chr(65+signal_idx)}: Frame PUBLISHED to Redis channel {channel}. Size: {len(frame_bytes)} bytes.")
                    else:
                        print(f"ERROR: Signal {chr(65+signal_idx)}: cv2.imencode failed (success={success}, buffer is None={buffer is None}).")
                else:
                    print(f"ERROR: Signal {chr(65+signal_idx)}: processed_frame is empty or invalid (size={processed_frame.size}, ndim={processed_frame.ndim}).")
            else:
                print(f"ERROR: Signal {chr(65+signal_idx)}: processed_frame returned by detector was None.")
            
            # Log emergency vehicle detection
            if emergency_count > 0:
                print(f"🚑 Emergency vehicle detected at Signal {chr(65+signal_idx)}: Count = {emergency_count}")
                
        except Exception as e:
            print(f"CRITICAL ERROR processing detection for Signal {signal_idx}: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc() # Print full traceback for deeper errors

    def reload_config_from_db(self):
        print("DetectionWorker: Reloading configuration from database...")
        # Re-initialize detection areas (will load from DB via initialize_system)
        self.initialize_system()
        # Re-initialize video captures based on updated VideoSource entries
        self.initialize_video_captures()
        print("DetectionWorker: Configuration reloaded successfully.")
    
    def reinitialize_video_capture(self, signal_idx):
        """Try to reinitialize video capture for a signal"""
        try:
            if self.video_caps[signal_idx]:
                self.video_caps[signal_idx].release()
                self.video_caps[signal_idx] = None
            
            signal = TrafficSignal.objects.get(signal_id=signal_idx)
            video_source = signal.video_source
            
            if video_source.is_active and video_source.video_path:
                self.video_caps[signal_idx] = cv2.VideoCapture(video_source.video_path)
                if self.video_caps[signal_idx].isOpened():
                    # --- NEW: Get and save dimensions upon reinitialization ---
                    actual_width = int(self.video_caps[signal_idx].get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(self.video_caps[signal_idx].get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    if video_source.width != actual_width or video_source.height != actual_height:
                        video_source.width = actual_width
                        video_source.height = actual_height
                        video_source.save(update_fields=['width', 'height']) # Save only these fields
                        print(f"Reinitialized Signal {chr(65+signal_idx)} and updated VideoSource dimensions to {actual_width}x{actual_height}")
                    else:
                        print(f"Reinitialized video capture for Signal {chr(65+signal_idx)}")
                        
                    self.video_caps[signal_idx].set(cv2.CAP_PROP_BUFFERSIZE, 2) # Apply settings again
                    self.video_caps[signal_idx].set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.video_caps[signal_idx].set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

                else:
                    print(f"ERROR: Signal {chr(65+signal_idx)}: Failed to reinitialize video source: {video_source.video_path}")
                    self.video_caps[signal_idx] = None
            else:
                print(f"WARNING: Video source not active or path is empty for Signal {chr(65+signal_idx)}. Not reinitializing.")
                self.video_caps[signal_idx] = None # Ensure it's None
                
        except Exception as e:
            print(f"Error reinitializing video capture for Signal {signal_idx}: {e}")
    
    def start(self):
        """Start the detection worker"""
        if not self.running:
            self.running = True
            self.initialize_video_captures()
            
            self.detection_thread = threading.Thread(target=self.capture_and_detect_frames, daemon=True)
            self.detection_thread.start()
            
            # Start the Redis control listener thread
            self.control_listener_thread = threading.Thread(target=self._redis_control_listener_thread_func, daemon=True)
            self.control_listener_thread.start()
            
            print("Detection worker started")
    
    def stop(self):
        """Stop the detection worker"""
        self.running = False
        
        # Release video captures
        for i, cap in enumerate(self.video_caps):
            if cap:
                cap.release()
                self.video_caps[i] = None
        
        # Stop Redis PubSub listener
        if self.redis_control_pubsub:
            self.redis_control_pubsub.unsubscribe(self.CONTROL_CHANNEL)
            print("DetectionWorker: Unsubscribed from Redis control channel.")

        # Wait for threads to finish
        if self.detection_thread:
            self.detection_thread.join(timeout=5.0)
        if self.control_listener_thread: # Add this
            self.control_listener_thread.join(timeout=5.0) # Add this
            
        print("Detection worker stopped")
    
    def get_current_frame(self, signal_idx):
        """Get the current raw frame for a signal"""
        if 0 <= signal_idx < len(self.current_frames):
            return self.current_frames[signal_idx]
        return None

# Global instance for use in views
detection_worker = None

def get_detection_worker():
    """Get or create the global detection worker instance"""
    global detection_worker
    if detection_worker is None:
        detection_worker = DetectionWorker()
    return detection_worker

def start_detection_worker():
    """Start the detection worker (called from management command or app startup)"""
    worker = get_detection_worker()
    worker.start()

def stop_detection_worker():
    """Stop the detection worker"""
    global detection_worker
    if detection_worker:
        detection_worker.stop()
        detection_worker = None

def main():
    worker = DetectionWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping detection worker...")
        worker.stop()

if __name__ == "__main__":
    main()
