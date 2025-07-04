from django.db import models
from django.contrib.auth.models import User
import json
from datetime import datetime
import cv2
import os

class JunctionSignals(models.Model):
    junction_name = models.CharField(max_length= 255)

class TrafficSignal(models.Model):
    """Model representing a traffic signal with its current state and configuration"""
    junction = models.ForeignKey(JunctionSignals, on_delete=models.CASCADE, related_name= 'signals', null= True)
    signal_id = models.IntegerField(unique=True, help_text="Signal ID (0-3 for A, B, C, D)")
    
    # Signal state
    current_state = models.CharField(max_length=10, default='RED', choices=[
        ('RED', 'Red'),
        ('YELLOW', 'Yellow'), 
        ('GREEN', 'Green')
    ])
    remaining_time = models.FloatField(default=0.0, help_text="Remaining time in current state")
    
    # Traffic detection data
    vehicle_count = models.IntegerField(default=0)
    traffic_weight = models.FloatField(default=0.0)
    avg_confidence = models.FloatField(default=0.0)
    
    # Vehicle type counts (stored as JSON)
    vehicle_type_counts = models.JSONField(default=dict, help_text="Counts for each vehicle type")
    
    # Signal timing configuration
    min_green_time = models.IntegerField(default=10)
    max_green_time = models.IntegerField(default=45)
    default_green_time = models.IntegerField(default=15)
    yellow_time = models.IntegerField(default=3)
    all_red_time = models.IntegerField(default=2)
    
    # Adaptive timing
    calculated_green_time = models.IntegerField(default=15)
    pending_green_time = models.IntegerField(default=0)
    
    # Congestion tracking
    congestion_level = models.CharField(max_length=10, default='LOW', choices=[
        ('LOW', 'Low'),
        ('MODERATE', 'Moderate'),
        ('HIGH', 'High'),
        ('SEVERE', 'Severe')
    ])
    congestion_score = models.FloatField(default=0.0)
    
    # Emergency tracking
    has_emergency_vehicle = models.BooleanField(default=False)
    emergency_vehicle_detected_time = models.DateTimeField(null=True, blank=True)
    emergency_vehicle_wait_time = models.FloatField(default=0.0)
    
    # Timestamps
    last_update_time = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'traffic_signals'
        ordering = ['signal_id']
    
    def __str__(self):
        return f"Signal {chr(65 + self.signal_id)} ({self.current_state})"
    
    def get_vehicle_type_counts(self):
        """Get vehicle type counts as a dictionary"""
        if isinstance(self.vehicle_type_counts, str):
            return json.loads(self.vehicle_type_counts)
        return self.vehicle_type_counts or {}
    
    def set_vehicle_type_counts(self, counts):
        """Set vehicle type counts from a dictionary"""
        self.vehicle_type_counts = counts
    
    def update_congestion_data(self, level, score):
        """Update congestion level and score"""
        self.congestion_level = level
        self.congestion_score = score
        self.save(update_fields=['congestion_level', 'congestion_score', 'last_update_time'])

class TrafficData(models.Model):
    signal = models.ForeignKey(TrafficSignal, on_delete=models.CASCADE, related_name='data_snapshots')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    vehicle_count = models.IntegerField(default=0, help_text="Total vehicles detected")
    traffic_weight = models.FloatField(default=0.0, help_text="Calculated traffic weight/density")
    green_time = models.IntegerField(null=True, blank=True, help_text="Green time of the signal at the moment of this snapshot")
    
    # Individual vehicle type counts
    auto_count = models.IntegerField(default=0)
    bike_count = models.IntegerField(default=0)
    bus_count = models.IntegerField(default=0)
    car_count = models.IntegerField(default=0)
    emergency_vehicles_count = models.IntegerField(default=0)
    truck_count = models.IntegerField(default=0)
    vehicle_type_counts_json = models.JSONField(default=dict, help_text="JSON representation of all vehicle type counts")

    class Meta:
        db_table = 'traffic_data' # Keep the same table name for continuity if desired
        ordering = ['-timestamp']
        verbose_name = "Traffic Data Snapshot"
        verbose_name_plural = "Traffic Data Snapshots"

    def __str__(self):
        return f"Snapshot for Signal {self.signal.signal_id} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

class TrafficLog(models.Model):
    """Model for logging traffic signal events and state changes"""
    signal = models.ForeignKey(TrafficSignal, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    event_type = models.CharField(max_length=50, choices=[
        ('STATE_CHANGE', 'State Change'),
        ('EMERGENCY_OVERRIDE', 'Emergency Override'),
        ('EMERGENCY_EXTEND', 'Emergency Extension'),
        ('DETECTION_UPDATE', 'Detection Update'),
        ('CONGESTION_ALERT', 'Congestion Alert'),
        ('TIMING_ADJUSTMENT', 'Timing Adjustment')
    ])
    
    details = models.JSONField(default=dict, help_text="Additional event details")
    
    class Meta:
        db_table = 'traffic_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.signal} - {self.event_type} at {self.timestamp}"

class DetectionArea(models.Model):
    """Model for storing detection areas for each signal"""
    signal = models.OneToOneField(TrafficSignal, on_delete=models.CASCADE, related_name='detection_area')
    area_points = models.JSONField(help_text="List of [x, y] coordinates defining the detection area")
    area_size = models.FloatField(default=0.0, help_text="Calculated area size")
    
    class Meta:
        db_table = 'detection_areas'
    
    def __str__(self):
        return f"Detection Area for Signal {self.signal}"

class VideoSource(models.Model):
    """Model for storing video source configurations"""
    signal = models.OneToOneField(TrafficSignal, on_delete=models.CASCADE, related_name='video_source')
    video_path = models.CharField(max_length=500, help_text="Path to video file or RTSP stream")
    is_active = models.BooleanField(default=True)
    last_frame_time = models.DateTimeField(null=True, blank=True)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'video_sources'
    
    def __str__(self):
        return f"Video Source for Signal {self.signal}"

class SystemSettings(models.Model):
    """Model for system-wide settings"""
    emergency_mode_active = models.BooleanField(default=False)
    detection_interval = models.FloatField(default=0.1, help_text="Detection loop interval in seconds")
    control_interval = models.FloatField(default=0.1, help_text="Control loop interval in seconds")
    log_retention_days = models.IntegerField(default=30, help_text="Days to retain logs")
    
    # YOLO model settings
    yolo_model_path = models.CharField(max_length=500, default="my_model (2).pt")
    confidence_threshold = models.FloatField(default=0.25)
    iou_threshold = models.FloatField(default=0.45)
    
    class Meta:
        db_table = 'system_settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return "System Settings"

class CongestionEvent(models.Model):
    """Model for tracking congestion events"""
    signal = models.ForeignKey(TrafficSignal, on_delete=models.CASCADE, related_name='congestion_events')
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=10, choices=[
        ('LOW', 'Low'),
        ('MODERATE', 'Moderate'),
        ('HIGH', 'High'),
        ('SEVERE', 'Severe')
    ])
    score = models.FloatField(default= 0.0)
    color = models.CharField(max_length= 10, null= True, blank= True)
    cause = models.CharField(max_length=255)
    resolution_time = models.IntegerField(null=True, blank=True, help_text="Time to resolve in seconds")
    
    class Meta:
        db_table = 'congestion_events'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Congestion Event at Signal {self.signal} - {self.severity}"

class SignalTimingLog(models.Model):
    """Model for logging signal timing changes"""
    signal = models.ForeignKey(TrafficSignal, on_delete=models.CASCADE, related_name='timing_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    green_time = models.IntegerField()
    yellow_time = models.IntegerField()
    red_time = models.IntegerField()
    reason = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'signal_timing_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Timing Log for Signal {self.signal} - {self.reason}"

