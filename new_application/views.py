from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .detection_worker import get_detection_worker, start_detection_worker, stop_detection_worker
import time
import threading
from .models import TrafficSignal, VideoSource, DetectionArea, JunctionSignals
from .traffic_control_worker import get_traffic_control_worker, start_traffic_control_worker, stop_traffic_control_worker # Keep if used by other views
from django.views.decorators.csrf import csrf_exempt
import redis
from django.conf import settings
import os
import json
from .utils import scale_points, calculate_area_size
from django.db import transaction
from django.db.utils import OperationalError

# Setup Redis connection (singleton for the Django process)
redis_client_for_pubsub = redis.StrictRedis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=getattr(settings, 'REDIS_DB', 0),
    decode_responses=False # Use bytes for frames
)

# Global dictionary to store the latest frame received from Redis for each signal
# {signal_id: frame_bytes}
latest_frames_cache = {}
# Global dictionary to store the latest signal states and system data from Redis
latest_dashboard_data_cache = {
    'signals': [], # List of signal dictionaries
    'system_overview': {
        'total_vehicles': 0,
        'system_efficiency': 0.0,
        'cycle_time': 0.0,
        'active_signal': 0, # Use integer signal_id
        'emergency_mode_active': False
    }
}

# Lock to protect access to the cache from multiple threads
frame_cache_lock = threading.Lock()
dashboard_data_cache_lock = threading.Lock()

# Flag to control the background listener thread
redis_listener_running = False
redis_listener_thread = None

def start_redis_listener():
    """Starts a single background thread to listen for all signal frames."""
    global redis_listener_running, redis_listener_thread

    if not redis_listener_running:
        print("Django Views: Starting Redis background listener thread...")
        redis_listener_running = True
        redis_listener_thread = threading.Thread(target=_listen_for_all_redis_updates, daemon=True)
        redis_listener_thread.start()
    else:
        print("Django Views: Redis background listener already running.")

def _listen_for_all_redis_updates():
    if not redis_client_for_pubsub:
        print("Django Views: Redis client not initialized, cannot listen for updates.")
        return

    pubsub_instance = redis_client_for_pubsub.pubsub()
    # Subscribe to specific frame channels using integer signal IDs (0, 1, 2, 3)
    pubsub_instance.subscribe('frame_channel_0', 'frame_channel_1', 'frame_channel_2', 'frame_channel_3')
    pubsub_instance.subscribe('dashboard_updates') # For signal/system data

    print("Django Views: Subscribed to specific frame channels and 'dashboard_updates'.")

    try:
        for message in pubsub_instance.listen():
            if message['type'] == 'message':
                channel_bytes = message['channel']
                data_bytes = message['data']
                channel_name = channel_bytes.decode('utf-8')

                if channel_name.startswith('frame_channel_'):
                    try:
                        # Extract signal_id (e.g., 'frame_channel_0' -> 0)
                        signal_id_int = int(channel_name.split('_')[-1])
                        with frame_cache_lock:
                            latest_frames_cache[signal_id_int] = data_bytes
                    except (ValueError, IndexError, UnicodeDecodeError) as e:
                        print(f"Django Views ERROR: Failed to parse frame channel or data: {e}, Message: {message}")
                    except Exception as e:
                        print(f"Django Views ERROR: Unexpected error in Redis frame listener: {e}")

                elif channel_name == 'dashboard_updates':
                    try:
                        data = json.loads(data_bytes.decode('utf-8'))
                        with dashboard_data_cache_lock:
                            # Update based on the type of dashboard update
                            if data.get('type') == 'signal_update':
                                latest_dashboard_data_cache['signals'] = data.get('signals', [])
                            elif data.get('type') == 'system_overview':
                                latest_dashboard_data_cache['system_overview'] = data.get('system_overview', {}) # Get the nested dictionary
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"Django Views ERROR: Failed to decode or parse JSON from dashboard update message: {e}, Message: {message}")
                    except Exception as e:
                        print(f"Django Views ERROR: Unexpected error in Redis dashboard listener: {e}")

            elif message['type'] == 'subscribe':
                print(f"Django Views: Redis {message['type']} confirmation for channel {message['channel'].decode('utf-8')}")

            if not redis_listener_running:
                break

    except redis.exceptions.ConnectionError as e:
        print(f"Django Views ERROR: Redis connection lost for listener: {e}")
    except Exception as e:
        print(f"Django Views ERROR: General error in Redis listener thread: {e}")
    finally:
        pubsub_instance.close()
        print("Django Views: Redis background listener thread stopped.")


@require_GET
def video_feed(request, signal_id):
    try:
        signal_id = int(signal_id) # Ensure signal_id is an integer
    except ValueError:
        return JsonResponse({"error": "Invalid signal ID"}, status=400)

    def generate_frames_from_cache():
        while True:
            with frame_cache_lock:
                frame_bytes = latest_frames_cache.get(signal_id)

            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                pass 
            time.sleep(0.05)

    return StreamingHttpResponse(
        generate_frames_from_cache(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@require_GET
def get_signal_states(request):
    with dashboard_data_cache_lock:
        cached_signals_data = latest_dashboard_data_cache.get('signals')

    if cached_signals_data:
        # If cache is populated, return cached data
        return JsonResponse({'signals': cached_signals_data})
    else:
        # Fallback to database if cache is empty (e.g., initial load or Redis issue)
        signals = TrafficSignal.objects.all().order_by('signal_id')
        data = [
            {
                'signal_id': s.signal_id,
                'current_state': s.current_state,
                'remaining_time': s.remaining_time,
                'vehicle_count': s.vehicle_count,
                'traffic_weight': s.traffic_weight,
                'congestion_level': s.congestion_level,
                'vehicle_type_counts': s.vehicle_type_counts,
            }
            for s in signals
        ]
        return JsonResponse({'signals': data})

@csrf_exempt
@require_GET
def update_emergency_mode(request):
    """Toggle emergency mode on/off via API (for demo, GET toggles)"""
    worker = get_traffic_control_worker()
    # Toggle emergency mode
    worker.set_emergency_mode(not worker.emergency_mode_active)
    return JsonResponse({'emergency_mode': worker.emergency_mode_active})

def dashboard_view(request):
    """Render a simple dashboard page (template to be created)"""
    return render(request, 'dashboard.html')

@csrf_exempt
@require_POST
def upload_video(request):
    if 'video_file' not in request.FILES:
        return JsonResponse({'error': 'No video_file provided'}, status=400)
    video_file = request.FILES['video_file']
    signal_id_int = request.POST.get('signal_id')

    if not signal_id_int:
        return JsonResponse({'error': 'signal_id not provided'}, status=400)

    try:
        signal_obj = TrafficSignal.objects.get(signal_id=signal_id_int)
    except ValueError:
        return JsonResponse({'error': 'Invalid signal_id format (must be integer)'}, status=400)
    except TrafficSignal.DoesNotExist:
        return JsonResponse({'error': f'TrafficSignal with ID {signal_id_int} does not exist'}, status=404)

    # Define upload directory within MEDIA_ROOT
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded_videos')
    os.makedirs(upload_dir, exist_ok=True) # Ensure directory exists

    # Create a unique filename (e.g., Signal0_timestamp.mp4)
    file_extension = os.path.splitext(video_file.name)[1]
    unique_filename = f"Signal{signal_id_int}_{int(time.time())}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    try:
        # Save the uploaded file to the server's file system
        with open(file_path, 'wb+') as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)

        # Update the VideoSource model with the server-side path
        VideoSource.objects.update_or_create(
            signal=signal_obj, # Use the TrafficSignal object
            defaults={
                'video_path': file_path, # Store the server-side absolute path
                'is_active': True # Assuming newly uploaded is active
            }
        )
        print(f"Uploaded video for Signal {signal_id_int} to {file_path}")
        redis_client_for_pubsub.publish('control_channel_detection_worker', 'reload_config')

        # Trigger detection worker to reload configuration
        get_detection_worker().reload_config_from_db()

        return JsonResponse({
            'message': f'File uploaded successfully for Signal {signal_id_int}',
            'file_path': file_path # Return the server-side path for confirmation
        })
    except Exception as e:
        print(f"Error uploading video for Signal {signal_id_int}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def save_area(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        print("Received data:", data)
        signal_id = data.get('signal_id')
        area = data.get('area')
        print(f"signal_id: {signal_id}, area: {area}")
        # Convert letter to number if needed
        letter_to_number = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        if isinstance(signal_id, str) and signal_id in letter_to_number:
            signal_id = letter_to_number[signal_id]
        if signal_id is None:
            return JsonResponse({'error': 'signal_id is required'}, status=400)
        if not area:
            return JsonResponse({'error': 'area is required'}, status=400)
        if len(area) != 4:
            return JsonResponse({'error': 'area must be a list of 4 points'}, status=400)
        MAX_RETRIES = 5
        RETRY_DELAY_SECONDS = 0.1 # Start with a small delay
        for attempt in range(MAX_RETRIES):
            try:
                with transaction.atomic():
                    signal = TrafficSignal.objects.get(signal_id=signal_id)
                    video_source = VideoSource.objects.get(signal=signal)

                    width = video_source.width
                    height = video_source.height

                    if width == 0 or height == 0:
                        return JsonResponse({'error': f'Video dimensions for Signal {signal_id} are not yet available. Please ensure the detection worker is running and the video source is valid.'}, status=409)

                    scaled_area = scale_points(area, width, height)

                    detection_area = DetectionArea.objects.get(signal=signal)
                    detection_area.area_points = scaled_area
                    detection_area.area_size = calculate_area_size(scaled_area) # Ensure this is the correct field name

                    detection_area.save() # The save operation is within the atomic block

                # If save succeeds, break the loop
                print(f"Area for signal {signal_id} saved successfully on attempt {attempt + 1}.")
                break # Exit retry loop on success

            except OperationalError as e: # Catch the specific database locked error
                if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                    print(f"Attempt {attempt + 1} failed for Signal {signal_id} (database is locked). Retrying in {RETRY_DELAY_SECONDS} seconds...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    RETRY_DELAY_SECONDS *= 1.5 # Exponential backoff
                else:
                    raise e # Re-raise if not a lock error or max retries reached
        # This sends a message to the detection worker to reload its configuration from the DB
        redis_client_for_pubsub.publish('control_channel_detection_worker', 'reload_config')
        print(f"Published 'reload_config' message for DetectionWorker after saving area for Signal {signal_id}.")
        return JsonResponse({'message': f'Area for signal {signal_id} saved successfully'})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data in request body.'}, status=400)
    except TrafficSignal.DoesNotExist:
        return JsonResponse({'error': f'Signal with ID {signal_id} not found.'}, status=404)
    except VideoSource.DoesNotExist:
        return JsonResponse({'error': f'Video source for Signal {signal_id} not found. Please upload a video first.'}, status=404)
    except Exception as e:
        print(f"Error saving area: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return JsonResponse({'error': f'An internal server error occurred while saving area: {e}'}, status=500)

@require_GET
def get_video(request):
    sources= {}
    signal_letters = ['A', 'B', 'C', 'D'] # Assuming you have 4 signals
    for i, letter in enumerate(signal_letters):
        try:
            signal = TrafficSignal.objects.get(signal_id=i)
            video_source = VideoSource.objects.get(signal=signal)
            abs_path = video_source.video_path
            rel_path = abs_path.replace('\\', '/')
            media_root = settings.MEDIA_ROOT.replace('\\', '/')
            if rel_path.startswith(media_root):
                rel_path = rel_path[len(media_root):]
            if not rel_path.startswith('/'):
                rel_path = '/' + rel_path
            video_url = settings.MEDIA_URL.rstrip('/') + rel_path
            sources[letter] = {'video_path': video_url}
        except (TrafficSignal.DoesNotExist, VideoSource.DoesNotExist):
            sources[letter] = {'video_path': ''}
    return JsonResponse({'sources': sources})

# getting the loaded areas
@require_GET
def get_area(request):
    signal_letters = ['A', 'B', 'C', 'D']
    areas = {}
    for area in DetectionArea.objects.select_related('signal').all():
        signal_id = getattr(area.signal, 'signal_id', None)
        if signal_id is not None and 0 <= signal_id < len(signal_letters):
            letter = signal_letters[signal_id]
            areas[letter] = area.area_points
    
    return JsonResponse({'area': areas})

@csrf_exempt
@require_POST
def add_junction(request):
    data = json.loads(request.body)
    name = data.get('name')
    print(name)
    if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
    junction, created = JunctionSignals.objects.get_or_create(junction_name = name)
    return JsonResponse({'id': junction.id, 'name': junction.junction_name}, status=201 if created else 200)

from datetime import datetime, date
from .import analytics_thread

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    
    raise TypeError ("Type %s not serializable" % type(obj))

def get_dashboard_analytics_data(request):
    try:
        historical_data = analytics_thread.get_historical_traffic_trends(duration_minutes=60) 
        vehicle_distribution = analytics_thread.get_current_traffic_distribution_smoothed(window_seconds=30)
        avg_confidences = analytics_thread.get_current_signal_metadata()
        congestion_data = analytics_thread.get_current_congestion_data()
        response_data = {
            'timestamps': historical_data['timestamps'],
            'vehicle_counts': historical_data['vehicle_counts'],
            'green_times': historical_data['green_times'],
            'vehicle_distribution': vehicle_distribution,
            'avg_confidences': avg_confidences,
            'congestion_data': congestion_data,
        }

        return JsonResponse(response_data, safe=False, json_dumps_params={'default': json_serial})

    except Exception as e:
        print(f"Error in get_dashboard_analytics_data view: {e}")
        return JsonResponse({'error': 'Failed to retrieve analytics data', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def start_workers_api(request):
    try:
        dw = get_detection_worker()
        tc = get_traffic_control_worker()

        messages = []
        if not dw.running:
            start_detection_worker()
            messages.append("Detection worker initiated.")
        else:
            messages.append("Detection worker already running.")
        
        if not tc.running:
            start_traffic_control_worker()
            messages.append("Traffic control worker initiated.")
        else:
            messages.append("Traffic control worker already running.")
        return JsonResponse({"status": "success", "message": " ".join(messages)})
    
    except Exception as e:
        print(f"API Error starting workers: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return JsonResponse({"status": "error", "message": f"Failed to start workers: {str(e)}"}, status=500)

@csrf_exempt
@require_POST
def stop_workers_api(request):
    try:
        messages = []
        # Stop detection worker
        det_worker = get_detection_worker()
        if det_worker.running:
            stop_detection_worker()
            messages.append("Detection worker stopping initiated.")
        else:
            messages.append("Detection worker not running.")

        # Stop traffic control worker
        tc_worker = get_traffic_control_worker()
        if tc_worker.running:
            stop_traffic_control_worker()
            messages.append("Traffic control worker stopping initiated.")
        else:
            messages.append("Traffic control worker not running.")

        return JsonResponse({"status": "success", "message": " ".join(messages)})
    except Exception as e:
        print(f"API Error stopping workers: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": f"Failed to stop workers: {str(e)}"}, status=500)
