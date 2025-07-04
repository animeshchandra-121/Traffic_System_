import datetime
from django.utils import timezone
from django.db.models import Avg, Max
from django.db import transaction, OperationalError
import time

# Make sure to import your models correctly based on their location
from .models import TrafficSignal, TrafficData, CongestionEvent 


def get_historical_traffic_trends(duration_minutes=60, num_signals=4):
    # ... (content of this function as provided in the previous detailed response) ...
    end_time = timezone.now()
    start_time = end_time - datetime.timedelta(minutes=duration_minutes)

    all_timestamps_set = set()
    temp_vehicle_counts = {i: [] for i in range(num_signals)}
    temp_green_times = {i: [] for i in range(num_signals)}

    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    for attempt in range(MAX_RETRIES):
        try:
            with transaction.atomic():
                snapshots = TrafficData.objects.filter(
                    timestamp__range=(start_time, end_time)
                ).order_by('timestamp', 'signal__signal_id')

                for s in snapshots:
                    signal_idx = s.signal.signal_id
                    if 0 <= signal_idx < num_signals:
                        all_timestamps_set.add(s.timestamp)
                        temp_vehicle_counts[signal_idx].append(s.vehicle_count)
                        temp_green_times[signal_idx].append(s.green_time)
                break
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                print(f"get_historical_traffic_trends: DB locked (attempt {attempt + 1}). Retrying in {RETRY_DELAY}s.")
                time.sleep(RETRY_DELAY)
                RETRY_DELAY *= 1.5
            else:
                print(f"get_historical_traffic_trends: Persistent database error after {attempt + 1} attempts: {e}")
                return {
                    'timestamps': [],
                    'vehicle_counts': [[] for _ in range(num_signals)],
                    'green_times': [[] for _ in range(num_signals)],
                }
        except Exception as e:
            print(f"Error fetching historical traffic trends: {e}")
            return {
                'timestamps': [],
                'vehicle_counts': [[] for _ in range(num_signals)],
                'green_times': [[] for _ in range(num_signals)],
            }

    all_timestamps_sorted = sorted(list(all_timestamps_set))
    
    return {
        'timestamps': [ts.isoformat() for ts in all_timestamps_sorted], # Convert datetime to ISO string for JSON
        'vehicle_counts': [temp_vehicle_counts[i] for i in range(num_signals)],
        'green_times': [temp_green_times[i] for i in range(num_signals)],
    }


def get_current_traffic_distribution_smoothed(window_seconds=30, num_signals=4):
    # ... (content of this function as provided in the previous detailed response) ...
    end_time = timezone.now()
    start_time = end_time - datetime.timedelta(seconds=window_seconds)

    distribution = [0] * num_signals

    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    for attempt in range(MAX_RETRIES):
        try:
            with transaction.atomic():
                signal_averages = TrafficData.objects.filter(
                    timestamp__range=(start_time, end_time)
                ).values('signal__signal_id').annotate(
                    avg_vehicle_count=Avg('vehicle_count')
                ).order_by('signal__signal_id')

                for entry in signal_averages:
                    signal_idx = entry['signal__signal_id']
                    if 0 <= signal_idx < num_signals:
                        distribution[signal_idx] = int(entry['avg_vehicle_count'] or 0)
                break
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                print(f"get_current_traffic_distribution_smoothed: DB locked (attempt {attempt + 1}). Retrying in {RETRY_DELAY}s.")
                time.sleep(RETRY_DELAY)
                RETRY_DELAY *= 1.5
            else:
                print(f"get_current_traffic_distribution_smoothed: Persistent database error after {attempt + 1} attempts: {e}")
                break
        except Exception as e:
            print(f"Error fetching smoothed traffic distribution: {e}")
            break

    for i in range(num_signals):
        if distribution[i] == 0:
            try:
                latest_signal_data = TrafficSignal.objects.get(signal_id=i)
                distribution[i] = latest_signal_data.vehicle_count
            except TrafficSignal.DoesNotExist:
                distribution[i] = 0

    return distribution


def get_current_signal_metadata(num_signals=4):
    # ... (content of this function as provided in the previous detailed response) ...
    avg_confidences = [0.0] * num_signals
    
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    for attempt in range(MAX_RETRIES):
        try:
            with transaction.atomic():
                signals = TrafficSignal.objects.all().order_by('signal_id')
                for signal in signals:
                    signal_idx = signal.signal_id
                    if 0 <= signal_idx < num_signals:
                        avg_confidences[signal_idx] = signal.avg_confidence
                break
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                print(f"get_current_signal_metadata: DB locked (attempt {attempt + 1}). Retrying in {RETRY_DELAY}s.")
                time.sleep(RETRY_DELAY)
                RETRY_DELAY *= 1.5
            else:
                print(f"get_current_signal_metadata: Persistent database error after {attempt + 1} attempts: {e}")
                break
        except Exception as e:
            print(f"Error fetching current signal metadata: {e}")
            break

    return avg_confidences


def get_current_congestion_data(num_signals=4):
    # ... (content of this function as provided in the previous detailed response) ...
    congestion_data = {}
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    for i in range(num_signals):
        for attempt in range(MAX_RETRIES):
            try:
                with transaction.atomic():
                    latest_event = CongestionEvent.objects.filter(
                        signal__signal_id=i
                    ).order_by('-timestamp').first()

                    if latest_event:
                        congestion_data[i] = {
                            'level': latest_event.severity,
                            'score': latest_event.score,
                            'color': latest_event.color,
                        }
                    else:
                        congestion_data[i] = {
                            'level': 'UNKNOWN',
                            'score': 0.0,
                            'color': '#bdc3c7',
                        }
                    break
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                    print(f"get_current_congestion_data (Signal {i}): DB locked (attempt {attempt + 1}). Retrying in {RETRY_DELAY}s.")
                    time.sleep(RETRY_DELAY)
                    RETRY_DELAY *= 1.5
                else:
                    print(f"get_current_congestion_data (Signal {i}): Persistent database error after {attempt + 1} attempts: {e}")
                    break
            except Exception as e:
                print(f"Error fetching congestion data for Signal {i}: {e}")
                break
    return congestion_data