import time
from collections import deque
from datetime import datetime
from .utils import letter_to_number
class EnhancedTrafficSignal:
    def __init__(self, signal_id):
        self.signal_id = signal_id
        self.min_green_time = 10
        self.max_green_time = 45
        self.default_green_time = 15
        self.yellow_time = 3
        self.all_red_time = 2

        # State variables
        self.current_state = 'RED'
        self.remaining_time = 0
        self.last_update_time = time.time()

        # Traffic data history
        self.vehicle_history = deque(maxlen=10)  # stores recent traffic weights

        # Vehicle count types (optional usage)
        self.vehicle_type_counts = {
            'car': 0,
            'truck': 0,
            'bus': 0,
            'motorcycle': 0,
            'bicycle': 0
        }

        # Runtime-calculated values
        self.vehicle_count = 0
        self.traffic_weight = 0
        self.calculated_green_time = self.default_green_time
        self.priority_mode = False

    def calculate_adaptive_green_time(self, vehicle_count, traffic_weight, time_of_day=None):
        """
        Dynamically calculates green light duration based on:
        - vehicle count
        - traffic weight
        - time of day (optional)
        """

        self.vehicle_count = vehicle_count
        self.traffic_weight = traffic_weight

        base_time = self.min_green_time

        # If no vehicles, fall back to default
        if vehicle_count == 0 or traffic_weight == 0:
            self.calculated_green_time = self.default_green_time
            return self.calculated_green_time

        # Density influence
                # Density influence
        density_time = min(traffic_weight * 3, self.max_green_time - base_time)

        # Time of day factor (peak/off-peak)
        time_factor = 1.0
        if time_of_day:
            hour = time_of_day.hour if isinstance(time_of_day, datetime) else datetime.now().hour
            if 7 <= hour <= 9 or 17 <= hour <= 19:  # Peak hours
                time_factor = 1.2
            elif 22 <= hour or hour <= 6:  # Late night
                time_factor = 0.8

        # Check traffic trend (history-aware boost)
        if len(self.vehicle_history) >= 3:
            avg_traffic = sum(self.vehicle_history) / len(self.vehicle_history)
            if traffic_weight > avg_traffic * 1.5:
                time_factor *= 1.3

        # Final green time calculation
        calculated_time = int(base_time + (density_time * time_factor))
        self.calculated_green_time = max(self.min_green_time, min(calculated_time, self.max_green_time))

        # Update history
        self.vehicle_history.append(traffic_weight)

        return self.calculated_green_time

    def reset(self):
        """
        Resets signal state for the next cycle.
        """
        self.current_state = 'RED'
        self.remaining_time = 0
        self.calculated_green_time = self.default_green_time
        self.vehicle_count = 0
        self.traffic_weight = 0
        self.vehicle_history.clear()

