import React, { useState, useEffect } from 'react';

const Settings = ({ onClose, signals, onSave }) => {
  const [settings, setSettings] = useState({
    A: { minGreenTime: 10, maxGreenTime: 45 },
    B: { minGreenTime: 10, maxGreenTime: 45 },
    C: { minGreenTime: 10, maxGreenTime: 45 },
    D: { minGreenTime: 10, maxGreenTime: 45 }
  });

  const [errors, setErrors] = useState({});

  // Initialize settings with current signal values
  useEffect(() => {
    if (signals) {
      const initialSettings = {};
      signals.forEach(signal => {
        initialSettings[signal.id] = {
          minGreenTime: signal.min_green_time || 10,
          maxGreenTime: signal.max_green_time || 45
        };
      });
      setSettings(initialSettings);
    }
  }, [signals]);

  const handleInputChange = (signal, field, value) => {
    setSettings(prev => ({
      ...prev,
      [signal]: {
        ...prev[signal],
        [field]: value
      }
    }));

    // Clear error for this field
    if (errors[`${signal}-${field}`]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[`${signal}-${field}`];
        return newErrors;
      });
    }
  };

  const validateSettings = () => {
    const newErrors = {};
    let isValid = true;

    Object.entries(settings).forEach(([signal, values]) => {
      const { minGreenTime, maxGreenTime } = values;

      // Validate min green time
      if (isNaN(minGreenTime) || minGreenTime < 5 || minGreenTime > 30) {
        newErrors[`${signal}-minGreenTime`] = 'Min green time must be between 5 and 30 seconds';
        isValid = false;
      }

      // Validate max green time
      if (isNaN(maxGreenTime) || maxGreenTime < 20 || maxGreenTime > 120) {
        newErrors[`${signal}-maxGreenTime`] = 'Max green time must be between 20 and 120 seconds';
        isValid = false;
      }

      // Validate min is less than max
      if (minGreenTime >= maxGreenTime) {
        newErrors[`${signal}-minGreenTime`] = 'Min green time must be less than max green time';
        isValid = false;
      }
    });

    setErrors(newErrors);
    return isValid;
  };

  const handleSave = () => {
    if (validateSettings()) {
      onSave(settings);
      onClose();
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content settings-modal">
        <h2>System Settings</h2>
        
        <div className="settings-section">
          <h3>Signal Timing Settings</h3>
          <div className="settings-grid">
            {Object.entries(settings).map(([signal, values]) => (
              <div key={signal} className="settings-card">
                <h4>Signal {signal}</h4>
                <div className="settings-input-group">
                  <div className="input-field">
                    <label>Min Green Time (seconds)</label>
                    <input
                      type="number"
                      value={values.minGreenTime}
                      onChange={(e) => handleInputChange(signal, 'minGreenTime', parseInt(e.target.value))}
                      min="5"
                      max="30"
                    />
                    {errors[`${signal}-minGreenTime`] && (
                      <span className="error-text">{errors[`${signal}-minGreenTime`]}</span>
                    )}
                  </div>
                  <div className="input-field">
                    <label>Max Green Time (seconds)</label>
                    <input
                      type="number"
                      value={values.maxGreenTime}
                      onChange={(e) => handleInputChange(signal, 'maxGreenTime', parseInt(e.target.value))}
                      min="20"
                      max="120"
                    />
                    {errors[`${signal}-maxGreenTime`] && (
                      <span className="error-text">{errors[`${signal}-maxGreenTime`]}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="modal-actions">
          <button onClick={onClose} className="control-btn gray">Cancel</button>
          <button onClick={handleSave} className="control-btn green">Save Settings</button>
        </div>
      </div>
    </div>
  );
};

export default Settings; 