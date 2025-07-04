import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// Utility to map signal letter to index
const letter_to_number = { A: 0, B: 1, C: 2, D: 3 };

const AnalyticsDashboard = ({ onClose, signals, systemData, analyticsData }) => {
  const [autoUpdate, setAutoUpdate] = useState(false);

  // Simulate data updates
  useEffect(() => {
    if (autoUpdate) {
      const interval = setInterval(updateData, 1000);
      return () => clearInterval(interval);
    }
  }, [autoUpdate]);

  const updateData = () => {
    const now = new Date();
    // Update analyticsData logic here
  };

  // Vehicle Count Trends Chart
  const vehicleCountData = {
    labels: analyticsData.timestamps,
    datasets: signals.map(signal => {
      const idx = letter_to_number[signal.id];
      const dataArr = analyticsData.vehicle_counts ? analyticsData.vehicle_counts[idx] : [];
      return {
        label: `Signal ${signal.id}`,
        data: dataArr,
        borderColor: getSignalColor(signal.id),
        backgroundColor: getSignalColor(signal.id, 0.1),
        tension: 0.4,
        fill: true
      };
    })
  };

  // Green Time Optimization Chart
  const greenTimeData = {
    labels: analyticsData.timestamps,
    datasets: signals.map(signal => {
      const idx = letter_to_number[signal.id];
      const dataArr = analyticsData.green_times ? analyticsData.green_times[idx] : [];
      return {
        label: `Signal ${signal.id}`,
        data: dataArr,
        borderColor: getSignalColor(signal.id),
        backgroundColor: getSignalColor(signal.id, 0.1),
        tension: 0.4,
        fill: true
      };
    })
  };

  // Current Signal Efficiencies Chart
  const efficiencyData = {
    labels: signals.map(s => `Signal ${s.id}`),
    datasets: [{
      label: 'Efficiency (%)',
      data: signals.map(s => s.efficiency),
      backgroundColor: signals.map(s => getEfficiencyColor(s.efficiency)),
      borderColor: signals.map(s => getEfficiencyColor(s.efficiency)),
      borderWidth: 1
    }]
  };

  // Traffic Distribution Chart
  const totalVehicles = signals.reduce((sum, s) => sum + s.vehicles, 0);
  const distributionData = {
    labels: signals.map(s => `Signal ${s.id}\n(${s.vehicles} vehicles)`),
    datasets: [{
      data: signals.map(s => s.vehicles),
      backgroundColor: signals.map(s => getSignalColor(s.id)),
      borderColor: signals.map(s => getSignalColor(s.id)),
      borderWidth: 1
    }]
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content analytics-modal" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
        <h2>Traffic Analytics Dashboard</h2>
        
        <div className="analytics-grid">
          <div className="analytics-card">
            <h3>Vehicle Count Trends</h3>
            <Line
              data={vehicleCountData}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: false
                  }
                },
                scales: {
                  x: {
                    type: 'time',
                    time: {
                      unit: 'minute',
                      displayFormats: {
                        second: 'HH:mm:ss',
                        minute: 'HH:mm',
                        hour: 'HH:mm',
                        day: 'MMM d',
                      },
                    },
                    title: {
                      display: true,
                      text: 'Time'
                    }
                  },
                  y: {
                    beginAtZero: true,
                    title: {
                      display: true,
                      text: 'Number of Vehicles'
                    }
                  }
                }
              }}
            />
          </div>

          <div className="analytics-card">
            <h3>Green Time Optimization</h3>
            <Line
              data={greenTimeData}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: false
                  }
                },
                scales: {
                  x: {
                    type: 'time',
                    time: {
                      unit: 'minute',
                      displayFormats: {
                        second: 'HH:mm:ss',
                        minute: 'HH:mm',
                        hour: 'HH:mm',
                        day: 'MMM d',
                      },
                    },
                    title: {
                      display: true,
                      text: 'Time'
                    }
                  },
                  y: {
                    beginAtZero: true,
                    title: {
                      display: true,
                      text: 'Green Time Duration (s)'
                    }
                  }
                }
              }}
            />
          </div>

          <div className="analytics-card">
            <h3>Current Signal Efficiencies</h3>
            <Bar
              data={efficiencyData}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    display: false
                  },
                  title: {
                    display: false
                  }
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                      display: true,
                      text: 'Efficiency (%)'
                    }
                  }
                }
              }}
            />
          </div>

          <div className="analytics-card">
            <h3>Traffic Distribution</h3>
            <div className="pie-chart-container">
              <Pie
                data={distributionData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'right'
                    },
                    title: {
                      display: false
                    }
                  }
                }}
              />
              <div className="total-vehicles">
                Total Vehicles: {totalVehicles}
              </div>
            </div>
          </div>
        </div>

        <div className="analytics-controls">
          <button
            className="control-btn green"
            onClick={updateData}
          >
            Update Analytics
          </button>
          <label className="auto-update-toggle">
            <input
              type="checkbox"
              checked={autoUpdate}
              onChange={(e) => setAutoUpdate(e.target.checked)}
            />
            Auto Update
          </label>
          <button
            className="control-btn gray"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// Helper functions for colors
const getSignalColor = (signalId, alpha = 1) => {
  const colors = {
    A: `rgba(52, 152, 219, ${alpha})`,  // Blue
    B: `rgba(46, 204, 113, ${alpha})`,  // Green
    C: `rgba(231, 76, 60, ${alpha})`,   // Red
    D: `rgba(241, 196, 15, ${alpha})`   // Yellow
  };
  return colors[signalId] || `rgba(149, 165, 166, ${alpha})`;
};

const getEfficiencyColor = (efficiency) => {
  if (efficiency >= 80) return 'rgba(46, 204, 113, 1)';  // Green
  if (efficiency >= 60) return 'rgba(241, 196, 15, 1)';  // Yellow
  return 'rgba(231, 76, 60, 1)';  // Red
};

export default AnalyticsDashboard; 