import React, { useState, useEffect, useCallback } from 'react';
import AreaSelectorVideo from "./dashboard/AreaSelectorVideo";
import VideoSourceConfig from "./dashboard/VideoSourceConfig";
import Settings from "./dashboard/Settings"; // Assuming you still use this
import AnalyticsDashboard from "./dashboard/AnalyticsDashboard";

const DashboardPage = ({ navigate }) => {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState([
    '[INFO] System initialized successfully',
    '[INFO] Camera feeds connected',
    '[INFO] YOLOv8 model loaded successfully'
  ]);
  const [showVideoConfig, setShowVideoConfig] = useState(false);
  const [emergencyMode, setEmergencyMode] = useState(false);

  // --- FIX 1: Initialize videoSources to store objects with path, width, and height ---
  const [videoSources, setVideoSources] = useState({
    A: { video_path: ''},
    B: { video_path: ''},
    C: { video_path: ''},
    D: { video_path: ''}
  });

  // Area selection state
  const [showAreaSelector, setShowAreaSelector] = useState(false);
  const [currentSignalIdx, setCurrentSignalIdx] = useState(0);
  const [areaPointsList, setAreaPointsList] = useState({ A: [], B: [], C: [], D: [] });

  const [showAnalytics, setShowAnalytics] = useState(false);
  const [analyticsData, setAnalyticsData] = useState({
    timestamps: [],
    vehicle_counts: { A: [], B: [], C: [], D: [] },
    green_times: { A: [], B: [], C: [], D: [] },
    vehicle_distribution: {},
    avg_confidences: {},
    congestion_data: {},
  });
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState(null);

  // --- NEW/MODIFIED FUNCTION: Fetch video source configurations from backend ---
  // This fetches ALL video paths and dimensions in one go
  const fetchVideoSourcesConfig = useCallback(async () => {
    try {
      // Assuming your backend endpoint is /api/get_video_sources/ and returns a structured JSON
      const response = await fetch('/api/get_video_sources/');
      if (!response.ok) throw new Error('Failed to fetch video sources configuration');
      const data = await response.json();
      // data.sources should be like:
      // {A: {video_path: '/media/vidA.mp4', width: 640, height: 480}, B: {...}, ...}
      setVideoSources(data.sources); // Update state with the fetched structured data
      setLogs(prev => [...prev, '[INFO] Video source configurations loaded.']);
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] Failed to load video source configurations: ${error.message}`]);
    }
  }, []); // No dependencies, as it's a general fetcher


  // --- MODIFIED useEffect: Fetch ALL necessary data on component mount ---
  useEffect(() => {
    const fetchAllInitialData = async () => {
      setLoading(true);
      // --- FIX 2: Fetch video sources FIRST ---
      await fetchVideoSourcesConfig(); // Populate videoSources state

      // Then fetch signals (your existing logic)
      try {
        const response = await fetch('/api/get_signal_states/'); // Assuming this is correct
        if (!response.ok) throw new Error('Failed to fetch signals');
        const data = await response.json();
        const mappedSignals = ['A', 'B', 'C', 'D'].map((id, idx) => {
          const s = data.signals.find(sig => sig.signal_id === idx);
          return s ? {
            id,
            vehicles: s.vehicle_count,
            weight: s.traffic_weight,
            status: s.current_state,
            congestion_level: s.congestion_level || 'UNKNOWN',
            congestion_score: 0,
            congestion_color: 'grey', // Ensure this property is consistently handled
            time: s.remaining_time || 0,
            efficiency: 0
          } : {
            id, vehicles: 0, weight: 0, status: 'unknown', congestion_level: 'UNKNOWN',
            congestion_score: 0, congestion_color: 'grey', time: 0, efficiency: 0
          };
        });
        setSignals(mappedSignals);
      } catch (error) {
        setLogs(prev => [...prev, `[ERROR] ${error.message}`]);
      } finally {
        setLoading(false);
      }
    };

    fetchAllInitialData();
    const interval = setInterval(fetchAllInitialData, 5000); // Poll every 5 seconds for updates
    return () => clearInterval(interval);
  }, [fetchVideoSourcesConfig]); // Re-run if fetchVideoSourcesConfig function reference changes


  const handleVideoConfigSave = (config) => {
    // 'config' should be the object returned by your backend after saving
    // Example: {A: {video_path: '...', width:..., height:...}, ...}
    setVideoSources(config); // Update state with the new structured configurations
    setShowVideoConfig(false);
    setLogs(prev => [...prev, '[INFO] Video sources configured successfully']);
    // You might want to re-fetch ALL data here if your config endpoint doesn't return everything
    // fetchVideoSourcesConfig();
  };

  // --- Area Selection Handlers ---
  const handleStartAreaSelection = () => {
    setAreaPointsList({ A: [], B: [], C: [], D: [] }); // Clear all area points
    setCurrentSignalIdx(0);
    setShowAreaSelector(true);
    setLogs(prev => [...prev, '[INFO] Starting area selection process']);
  };

  const handleAreaSave = async (points) => {
    const signalLetters = ["A", "B", "C", "D"];
    const currentSignal = signalLetters[currentSignalIdx];
    const newAreaPointsList = { ...areaPointsList, [currentSignal]: points };
    setAreaPointsList(newAreaPointsList);

    // Save area to backend
    try {
      const payload = {
        signal_id: currentSignal, // 'A', 'B', etc.
        area: points
      };
      const response = await fetch('/api/save_area/', { // Assuming a /api/save_area/ endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const errorData = await response.json(); // Try to get error message from response body
        throw new Error(errorData.error || `Failed to save area for signal ${currentSignal}`);
      }
      setLogs(prev => [...prev, `[INFO] Area for Signal ${currentSignal} saved to backend.`]);
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] Failed to save area for Signal ${currentSignal}: ${error.message}`]);
    }

    if (currentSignalIdx < 3) {
      // --- FIX 3 (continued): No need to fetch video for next signal either ---
      setCurrentSignalIdx(prev => prev + 1);
      setLogs(prev => [...prev, `[INFO] Area for Signal ${currentSignal} saved. Moving to next signal.`]);
    } else {
      setShowAreaSelector(false);
      setLogs(prev => [...prev, '[INFO] All signal areas configured successfully']);
    }
  };

  const handleAreaSelectionCancel = () => {
    setShowAreaSelector(false);
    setCurrentSignalIdx(0);
    setLogs(prev => [...prev, '[INFO] Area selection cancelled']);
  };

  // --- Fetch emergency mode state on mount and after toggle ---
  const fetchEmergencyMode = useCallback(async () => {
    try {
      const response = await fetch('/api/emergency/');
      if (!response.ok) throw new Error('Failed to fetch emergency mode');
      const data = await response.json();
      setEmergencyMode(data.emergency_mode);
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] Failed to fetch emergency mode: ${error.message}`]);
    }
  }, []);

  useEffect(() => {
    fetchEmergencyMode();
  }, [fetchEmergencyMode]);

  const handleToggleEmergency = async () => {
    try {
      const response = await fetch('/api/emergency/');
      if (!response.ok) throw new Error('Failed to toggle emergency mode');
      const data = await response.json();
      setEmergencyMode(data.emergency_mode);
      setLogs(prev => [...prev, `[INFO] Emergency mode ${data.emergency_mode ? 'activated' : 'deactivated'}`]);
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] Failed to toggle emergency mode: ${error.message}`]);
    }
  };

  const fetchAnalyticsData = useCallback(async () => {
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const response = await fetch('/api/analytics/');
      if (!response.ok) throw new Error('Failed to fetch analytics data');
      const data = await response.json();
      setAnalyticsData(data);
    } catch (error) {
      setAnalyticsError(error.message);
    } finally {
      setAnalyticsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (showAnalytics) {
      fetchAnalyticsData();
    }
  }, [showAnalytics, fetchAnalyticsData]);

  if (loading && signals.length === 0) return <div>Loading...</div>; // Show loading if no signals are loaded

  return (
    <>
      <div className="dashboard-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: '1400px', margin: '0 auto', padding: '0 2rem' }}>
          <h1>Traffic Management Dashboard</h1>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button onClick={() => setShowVideoConfig(true)} className="main-btn" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
              📹 Configure Video Sources
            </button>
          </div>
        </div>
      </div>
      <main className="dashboard-main" style={{ display: 'flex', flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'center', minHeight: '80vh', gap: '2rem' }}>
        {/* Left: Video Grid */}
        <div className="video-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', margin: '2rem 0' }}>
          {signals.length > 0 ? signals.map((signal, signalIndex) => (
            <div key={signal.id} className="signal-card">
              <div className="signal-title">Signal {signal.id}</div>
              <div className="video-feed">
                <img
                  src={`/video_feed/${signalIndex}/`}
                  alt={`Signal ${signal.id} video`}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              <div className="signal-info">
                <div className={`status-label ${signal.status}`}>{signal.status.toUpperCase()}</div>
                <div className="time-label">Time: {signal.time}s</div>
                <div className="count-label">Vehicles: {signal.vehicles} | Weight: {signal.weight}</div>
                <div className={`congestion-indicator ${signal.congestion_level && signal.congestion_level.toLowerCase()}`.trim()} style={{ marginTop: '0.5rem' }}>
                  <span style={{ fontSize: '1.1em', marginRight: '0.5em' }}>🚦</span>
                  {signal.congestion_level ? signal.congestion_level.charAt(0) + signal.congestion_level.slice(1).toLowerCase() : 'Unknown'}
                </div>
              </div>
            </div>
          )) : (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem' }}>
              No signal data available. Please configure video sources.
            </div>
          )}
        </div>
        {/* Right: System Log and New Areas button */}
        <div style={{ minWidth: '350px', maxWidth: '400px', marginTop: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'stretch', gap: '1.5rem' }}>
          <div className="system-log" style={{ width: '100%' }}>
            <div className="log-title">System Log</div>
            <textarea className="log-text" readOnly value={logs.join('\n')} style={{ width: '100%', minHeight: '250px' }} />
          </div>
          <button
            className="control-btn blue"
            style={{ width: '100%', fontSize: '1.1rem', padding: '1rem 0' }}
            onClick={handleStartAreaSelection}
          >🎯 New Areas
          </button>
          <button
            className="control-btn green"
            style={{ width: '100%', fontSize: '1.1rem', padding: '1rem 0' }}
            onClick={async () => {
              try {
                setLogs(prev => [...prev, '[INFO] Loading saved areas...']);
                const response = await fetch('/api/get_area/');
                if (!response.ok) throw new Error('Failed to fetch areas');
                const data = await response.json();
                if (data.areas) {
                  setAreaPointsList(data.areas);
                  setLogs(prev => [...prev, '[INFO] Areas loaded successfully.']);
                } else {
                  setLogs(prev => [...prev, '[ERROR] No area data found.']);
                }
              } catch (err) {
                setLogs(prev => [...prev, `[ERROR] Failed to load areas: ${err.message}`]);
              }
            }}
          >📁 Load Areas
          </button>
          <button
            onClick={handleToggleEmergency}
            className={`control-btn ${emergencyMode ? 'red' : 'orange'}`}
            style={{ width: '100%', fontSize: '1.1rem', padding: '1rem 0' }}
          >
            🚨 Emergency Mode
          </button>
          {/* Start/Stop Workers Buttons */}
          <button
            className="control-btn green"
            style={{ width: '100%', fontSize: '1.1rem', padding: '1rem 0' }}
            onClick={async () => {
              try {
                setLogs(prev => [...prev, '[INFO] Starting workers...']);
                const response = await fetch('/api/start_workers_api/', { method: 'POST' });
                if (!response.ok) throw new Error('Failed to start workers');
                setLogs(prev => [...prev, '[INFO] Workers started successfully.']);
              } catch (err) {
                setLogs(prev => [...prev, `[ERROR] Failed to start workers: ${err.message}`]);
              }
            }}
          >
            ▶️ Start Workers
          </button>
          <button
            className="control-btn red"
            style={{ width: '100%', fontSize: '1.1rem', padding: '1rem 0' }}
            onClick={async () => {
              try {
                setLogs(prev => [...prev, '[INFO] Stopping workers...']);
                const response = await fetch('/api/stop_workers_api/', { method: 'POST' });
                if (!response.ok) throw new Error('Failed to stop workers');
                setLogs(prev => [...prev, '[INFO] Workers stopped successfully.']);
              } catch (err) {
                setLogs(prev => [...prev, `[ERROR] Failed to stop workers: ${err.message}`]);
              }
            }}
          >
            ⏹️ Stop Workers
          </button>
          <button
            className="control-btn purple"
            style={{ width: '100%', fontSize: '1.1rem', padding: '1rem 0' }}
            onClick={() => setShowAnalytics(true)}
          >📊 Analytics
          </button>
        </div>
        {showVideoConfig && (
          <div className="modal-overlay">
            <VideoSourceConfig
              onSave={handleVideoConfigSave}
              onCancel={() => setShowVideoConfig(false)}
              initialSources={videoSources}
            />
          </div>
        )}
        {showAreaSelector && (
          <div className="modal-overlay">
            <div className="modal-content" style={{ maxWidth: '800px' }}>
              <h3 style={{ textAlign: 'center', marginBottom: '1rem' }}>
                Define Area for Signal {["A", "B", "C", "D"][currentSignalIdx]}
              </h3>
              <AreaSelectorVideo
                videoSrc={videoSources[["A", "B", "C", "D"][currentSignalIdx]]?.video_path}
                onSave={handleAreaSave}
                onCancel={handleAreaSelectionCancel}
                signalId={["A", "B", "C", "D"][currentSignalIdx]}
                existingPoints={areaPointsList[["A", "B", "C", "D"][currentSignalIdx]] || []}
              />
            </div>
          </div>
        )}
        {showAnalytics && (
          <div className="modal-overlay">
            <AnalyticsDashboard
              onClose={() => setShowAnalytics(false)}
              signals={signals}
              systemData={{}}
              analyticsData={analyticsData}
            />
          </div>
        )}
      </main>
    </>
  );
};

export default DashboardPage;