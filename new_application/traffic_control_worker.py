import os
import time
import threading
from datetime import datetime


# Configure Django environment
if __name__ == "__main__" :
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_system.settings')
    django.setup()

else:
    pass

from .models import TrafficSignal, TrafficLog, SignalTimingLog, CongestionEvent, SystemSettings
from .EnhancedTrafficSignal import EnhancedTrafficSignal

class TrafficControlWorker:
    """Background worker for traffic signal control and state transitions"""
    
    def __init__(self):
        self.running = False
        self.control_thread = None
        
        # Global state for emergency mode
        self.emergency_mode_active = False
        self.interrupted_signal_idx = None
        self.interrupted_signal_remaining = None
        self._emergency_force_red = False
        
        # Current system state
        self.current_system_signal = 0
        self.last_system_update_time = time.time()
        
        # Load system settings
        self.settings, _ = SystemSettings.objects.get_or_create(id=1)
        
        # Initialize signals
        self.initialize_signals()
    
    def initialize_signals(self):
        """Initialize all traffic signals in the database"""
        try:
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
                
                if created:
                    print(f"Created new signal {chr(65+i)}")
            
            print("Traffic signals initialized")
            
        except Exception as e:
            print(f"Error initializing system: {type(e)} - {e}")
    
    def run_traffic_control_loop(self):
        """Main loop for handling signal transitions and adaptive timing"""
        print("Starting traffic control loop...")
        
        # Initial setup for signal A
        self.run_initial_detection_for_signal(0)
        
        while self.running:
            try:
                current_time = time.time()
                elapsed = current_time - self.last_system_update_time
                self.last_system_update_time = current_time
                
                # Ensure elapsed time is reasonable
                if elapsed > 1.0:
                    elapsed = 1.0
                    print(f"Warning: Large time gap detected ({elapsed:.1f}s)")
                
                # Handle signal transitions
                self.handle_signal_transitions(elapsed)
                
                # Sleep based on control interval setting
                time.sleep(self.settings.control_interval)
                
            except Exception as e:
                print(f"Error in traffic control loop: {e}")
                time.sleep(1.0)  # Wait longer on error
    
    def run_initial_detection_for_signal(self, signal_idx):
        """Run initial detection for a signal and set it to GREEN"""
        try:
            signal = TrafficSignal.objects.get(signal_id=signal_idx)
            
            # Create logic signal instance
            logic_signal = EnhancedTrafficSignal(signal.signal_id)
            logic_signal.min_green_time = signal.min_green_time
            logic_signal.max_green_time = signal.max_green_time
            logic_signal.yellow_time = signal.yellow_time
            logic_signal.all_red_time = signal.all_red_time
            logic_signal.default_green_time = signal.default_green_time
            
            # Calculate green time based on current vehicle data
            green_time = logic_signal.calculate_adaptive_green_time(
                signal.vehicle_count, 
                signal.traffic_weight, 
                datetime.now()
            )
            
            # Update signal state
            signal.current_state = 'GREEN'
            signal.remaining_time = green_time
            signal.calculated_green_time = green_time
            signal.save()
            
            # Log the state change
            TrafficLog.objects.create(
                signal=signal,
                event_type='STATE_CHANGE',
                details={
                    'old_state': 'RED',
                    'new_state': 'GREEN',
                    'reason': 'initial_adaptive',
                    'green_time': green_time
                }
            )
            
            # Log timing change
            SignalTimingLog.objects.create(
                signal=signal,
                green_time=green_time,
                yellow_time=signal.yellow_time,
                red_time=signal.all_red_time,
                reason='initial_adaptive'
            )
            
            print(f"🟢 Initial: Signal {chr(65+signal_idx)} → GREEN for {green_time:.1f}s")
            
        except Exception as e:
            print(f"Error in initial detection for Signal {signal_idx}: {e}")
    
    def run_detection_for_next_signal(self, signal_idx):
        """Run detection for next signal during yellow phase"""
        try:
            signal = TrafficSignal.objects.get(signal_id=signal_idx)
            
            # Create logic signal instance
            logic_signal = EnhancedTrafficSignal(signal.signal_id)
            logic_signal.min_green_time = signal.min_green_time
            logic_signal.max_green_time = signal.max_green_time
            logic_signal.yellow_time = signal.yellow_time
            logic_signal.all_red_time = signal.all_red_time
            logic_signal.default_green_time = signal.default_green_time
            
            # Calculate green time based on current vehicle data
            green_time = logic_signal.calculate_adaptive_green_time(
                signal.vehicle_count,
                signal.traffic_weight,
                datetime.now()
            )
            
            # Set pending green time
            signal.pending_green_time = green_time
            signal.calculated_green_time = green_time
            signal.save()
            
            print(f"[Detection during Yellow] Signal {chr(65+signal_idx)}: Green={green_time}s")
            
        except Exception as e:
            print(f"Error in detection for next signal {signal_idx}: {e}")
    
    def handle_signal_transitions(self, elapsed):
            """Handle signal state transitions"""
            try:
                # Fetch all signals to determine the next one and ensure consistency
                all_signals = {s.signal_id: s for s in TrafficSignal.objects.all()}
                active_signal = all_signals.get(self.current_system_signal)

                if not active_signal:
                    print(f"ERROR: Active signal {self.current_system_signal} not found in DB. Reinitializing signals.")
                    self.initialize_signals() # Attempt to recover
                    return

                # Update remaining time for the active signal
                if active_signal.remaining_time > 0:
                    active_signal.remaining_time = max(0, active_signal.remaining_time - elapsed)
                    active_signal.save()

                # DEBUG PRINT: Always show current state and time
                print(f"Traffic Control: Signal {chr(65 + active_signal.signal_id)} is {active_signal.current_state}, Time Left: {active_signal.remaining_time:.1f}s")

                # Emergency mode logic (prioritized)
                if self.emergency_mode_active:
                    self.handle_emergency_mode(active_signal)
                    return # Exit if emergency mode is active, it handles its own transitions

                # Normal state transitions
                if active_signal.remaining_time <= 0:
                    if active_signal.current_state == 'GREEN':
                        # Transition active signal to YELLOW
                        active_signal.current_state = 'YELLOW'
                        active_signal.remaining_time = active_signal.yellow_time
                        active_signal.save()
                        TrafficLog.objects.create(
                            signal=active_signal, event_type='STATE_CHANGE',
                            details={'old_state': 'GREEN', 'new_state': 'YELLOW'}
                        )
                        print(f"🟡 Signal {chr(65 + active_signal.signal_id)} → YELLOW for {active_signal.yellow_time:.1f}s")

                        # Run detection for the NEXT signal while current is YELLOW
                        next_signal_idx = (self.current_system_signal + 1) % 4
                        self.run_detection_for_next_signal(next_signal_idx)

                    elif active_signal.current_state == 'YELLOW':
                        # Transition active signal to RED
                        active_signal.current_state = 'RED'
                        active_signal.remaining_time = active_signal.all_red_time # Use all_red_time here
                        active_signal.save()
                        TrafficLog.objects.create(
                            signal=active_signal, event_type='STATE_CHANGE',
                            details={'old_state': 'YELLOW', 'new_state': 'RED'}
                        )
                        print(f"🔴 Signal {chr(65 + active_signal.signal_id)} → RED for {active_signal.all_red_time:.1f}s")

                        # All other signals should already be RED, but ensure they are.
                        for s_id, s in all_signals.items():
                            if s_id != active_signal.signal_id and s.current_state != 'RED':
                                s.current_state = 'RED'
                                s.remaining_time = 0 # Or a short all_red_time if they just turned red
                                s.save()
                                TrafficLog.objects.create(
                                    signal=s, event_type='STATE_CHANGE',
                                    details={'old_state': s.current_state, 'new_state': 'RED', 'reason': 'all_red_sync'}
                                )
                                print(f"🔴 Sync: Signal {chr(65+s_id)} → RED")


                    elif active_signal.current_state == 'RED':
                        # This is the point where the signal has completed its RED phase (or was already RED)
                        # and it's time to advance the cycle to the next signal.

                        # Find the next signal in the cycle
                        next_signal_idx = (self.current_system_signal + 1) % 4
                        next_signal = all_signals.get(next_signal_idx)
                        
                        if not next_signal: # Defensive check
                            print(f"ERROR: Next signal {next_signal_idx} not found. Skipping cycle advance.")
                            return

                        # Transition the NEXT signal to GREEN
                        green_time_for_next = next_signal.pending_green_time if next_signal.pending_green_time > 0 else next_signal.default_green_time

                        next_signal.current_state = 'GREEN'
                        next_signal.remaining_time = green_time_for_next
                        next_signal.pending_green_time = 0 # Reset pending time
                        next_signal.save()

                        TrafficLog.objects.create(
                            signal=next_signal, event_type='STATE_CHANGE',
                            details={'old_state': 'RED', 'new_state': 'GREEN', 'reason': 'cycle_advance', 'green_time': green_time_for_next}
                        )
                        SignalTimingLog.objects.create(
                            signal=next_signal,
                            green_time=green_time_for_next,
                            yellow_time=next_signal.yellow_time,
                            red_time=next_signal.all_red_time,
                            reason='automatic' if next_signal.pending_green_time > 0 else 'default'
                        )
                        print(f"🟢 Signal {chr(65 + next_signal_idx)} → GREEN for {green_time_for_next:.1f}s")

                        # Advance the system's current signal to the new GREEN signal
                        self.current_system_signal = next_signal_idx
                        
            except Exception as e:
                print(f"CRITICAL ERROR in handle_signal_transitions: {type(e).__name__} - {e}")
                import traceback
                traceback.print_exc()
    
    def handle_emergency_mode(self, active_signal):
        """Handle emergency mode logic"""
        try:
            emergency_detected = False
            emergency_signal_idx = None
            
            # Check all signals for emergency vehicles
            for i in range(4):
                signal = TrafficSignal.objects.get(signal_id=i)
                if signal.has_emergency_vehicle:
                    emergency_detected = True
                    emergency_signal_idx = i
                    break
            
            if emergency_detected:
                # Emergency in a different signal
                if active_signal.current_state == 'GREEN' and self.current_system_signal != emergency_signal_idx:
                    if self.interrupted_signal_idx is None and active_signal.remaining_time > 8.0:
                        self.interrupted_signal_idx = self.current_system_signal
                        self.interrupted_signal_remaining = active_signal.remaining_time
                    else:
                        self.interrupted_signal_idx = None
                        self.interrupted_signal_remaining = None
                    
                    active_signal.current_state = 'YELLOW'
                    active_signal.remaining_time = 3.0
                    active_signal.save()
                    self._emergency_force_red = True
                    
                    # Log emergency override
                    TrafficLog.objects.create(
                        signal=active_signal,
                        event_type='EMERGENCY_OVERRIDE',
                        details={
                            'from_signal': chr(65+self.current_system_signal),
                            'to_state': 'YELLOW',
                            'reason': 'emergency_elsewhere'
                        }
                    )
                    
                    print(f"🚑 Emergency vehicle at Signal {chr(65+emergency_signal_idx)} - Forcing Signal {chr(65+self.current_system_signal)} to YELLOW for 3s")
                    return
                
                elif active_signal.current_state == 'YELLOW' and self.current_system_signal != emergency_signal_idx:
                    if self._emergency_force_red and active_signal.remaining_time <= 0:
                        active_signal.current_state = 'RED'
                        active_signal.remaining_time = 0
                        active_signal.save()
                        
                        # Log emergency override
                        TrafficLog.objects.create(
                            signal=active_signal,
                            event_type='EMERGENCY_OVERRIDE',
                            details={
                                'from_signal': chr(65+self.current_system_signal),
                                'to_state': 'RED',
                                'reason': 'emergency_yellow_to_red'
                            }
                        )
                        
                        # Switch to emergency signal
                        self.current_system_signal = emergency_signal_idx
                        emergency_signal = TrafficSignal.objects.get(signal_id=emergency_signal_idx)
                        
                        # Create logic signal for emergency
                        logic_signal = EnhancedTrafficSignal(emergency_signal.signal_id)
                        logic_signal.min_green_time = emergency_signal.min_green_time
                        logic_signal.max_green_time = emergency_signal.max_green_time
                        logic_signal.yellow_time = emergency_signal.yellow_time
                        logic_signal.all_red_time = emergency_signal.all_red_time
                        logic_signal.default_green_time = emergency_signal.default_green_time
                        
                        # Calculate extended green time for emergency
                        emergency_count = emergency_signal.vehicle_type_counts.get('emergency_vehicles', 0)
                        extended_time = min(emergency_count * 2 + 10, emergency_signal.max_green_time)
                        
                        emergency_signal.current_state = 'GREEN'
                        emergency_signal.remaining_time = extended_time
                        emergency_signal.save()
                        
                        # Log emergency activation
                        TrafficLog.objects.create(
                            signal=emergency_signal,
                            event_type='STATE_CHANGE',
                            details={
                                'old_state': 'RED',
                                'new_state': 'GREEN',
                                'reason': 'emergency_force_green',
                                'green_time': extended_time
                            }
                        )
                        
                        print(f"Signal {chr(65+emergency_signal_idx)}: Forced GREEN due to emergency. Remaining time: {extended_time:.1f}s")
                        self._emergency_force_red = False
                        return
                
                elif active_signal.current_state == 'GREEN' and self.current_system_signal == emergency_signal_idx:
                    # Extend green time for emergency vehicle
                    emergency_count = active_signal.vehicle_type_counts.get('emergency_vehicles', 0)
                    if emergency_count > 0:
                        extended_time = min(emergency_count * 2 + 10, active_signal.max_green_time)
                        active_signal.remaining_time = max(active_signal.remaining_time, extended_time)
                        active_signal.save()
                        
                        # Log emergency extension
                        TrafficLog.objects.create(
                            signal=active_signal,
                            event_type='EMERGENCY_EXTEND',
                            details={
                                'signal_id': active_signal.signal_id,
                                'extended_time': extended_time
                            }
                        )
                        
                        print(f"🚑 Emergency vehicle at current Signal {chr(65+self.current_system_signal)} - Extended green time to {active_signal.remaining_time:.1f}s")
                        return
            
            # Resume interrupted signal if no emergency detected
            if self.interrupted_signal_idx is not None:
                if active_signal.current_state in ['YELLOW', 'RED'] and self.current_system_signal == emergency_signal_idx:
                    resume_idx = self.interrupted_signal_idx
                    resume_time = self.interrupted_signal_remaining
                    
                    self.interrupted_signal_idx = None
                    self.interrupted_signal_remaining = None
                    
                    if resume_time is not None and resume_time > 8.0:
                        resume_signal = TrafficSignal.objects.get(signal_id=resume_idx)
                        resume_signal.current_state = 'GREEN'
                        resume_signal.remaining_time = resume_time
                        resume_signal.save()
                        self.current_system_signal = resume_idx
                        
                        # Log resume
                        TrafficLog.objects.create(
                            signal=resume_signal,
                            event_type='STATE_CHANGE',
                            details={
                                'old_state': 'RED',
                                'new_state': 'GREEN',
                                'reason': 'resume_after_emergency',
                                'green_time': resume_time
                            }
                        )
                        
                        print(f"Resuming from interrupted Signal {chr(65+resume_idx)} after emergency (with {resume_time:.1f}s left).")
                        return
                        
        except Exception as e:
            print(f"Error in emergency mode handling: {e}")
    
    def start(self):
        """Start the traffic control worker"""
        if not self.running:
            self.running = True
            self.control_thread = threading.Thread(target=self.run_traffic_control_loop, daemon=True)
            self.control_thread.start()
            print("Traffic control worker started")
    
    def stop(self):
        """Stop the traffic control worker"""
        self.running = False
        
        # Wait for thread to finish
        if self.control_thread:
            self.control_thread.join(timeout=5.0)
        
        print("Traffic control worker stopped")
    
    def set_emergency_mode(self, active):
        """Set emergency mode on/off"""
        self.emergency_mode_active = active
        
        # Update system settings
        self.settings.emergency_mode_active = active
        self.settings.save()
        
        status = "ACTIVATED" if active else "DEACTIVATED"
        print(f"Emergency mode {status}")
    
    def get_current_signal(self):
        """Get the current active signal"""
        return self.current_system_signal

# Global instance for use in views
traffic_control_worker = None

def get_traffic_control_worker():
    """Get or create the global traffic control worker instance"""
    global traffic_control_worker
    if traffic_control_worker is None:
        traffic_control_worker = TrafficControlWorker()
    return traffic_control_worker

def start_traffic_control_worker():
    """Start the traffic control worker"""
    worker = get_traffic_control_worker()
    worker.start()

def stop_traffic_control_worker():
    """Stop the traffic control worker"""
    global traffic_control_worker
    if traffic_control_worker:
        traffic_control_worker.stop()
        traffic_control_worker = None

def main():
    worker = TrafficControlWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping traffic control worker...")
        worker.stop()

if __name__ == "__main__":
    main() 