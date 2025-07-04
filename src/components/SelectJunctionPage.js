import React, { useState } from 'react';
import Header from './Header';

const SelectJunctionPage = ({ navigate }) => {
  const [selectedJunction, setSelectedJunction] = useState('');

  const predefinedJunctions = [
    "Junction 1 - Main Street",
    "Junction 2 - Downtown",
    "Junction 3 - Industrial Area",
    "Junction 4 - Residential Zone"
  ];

  const handleProceed = async () => {
    if (!selectedJunction) return;
    
    try {
      // Try to add the junction to the backend
      const res = await fetch('/api/add_junction/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selectedJunction })
      });
      
      if (!res.ok) {
        throw new Error('Failed to create junction');
      }
      
      const data = await res.json();
      // Navigate to dashboard with the returned junction id
      navigate('dashboard', data.id);
    } catch (error) {
      console.error('Error creating junction:', error);
      alert('Failed to create junction. Please try again.');
    }
  };

  return (
    <>
      <Header />
      <div className="container">
        <div className="card">
          <h1>Select Junction</h1>
          <p className="subtitle">Choose a junction to monitor and manage traffic</p>
          
          <div style={{ textAlign: 'left' }}>
            <div className="form-group">
              <label htmlFor="junction">
                📍 Junction Location
              </label>
              <select
                id="junction"
                value={selectedJunction}
                onChange={e => setSelectedJunction(e.target.value)}
                className="form-control"
              >
                <option value="">Select a junction...</option>
                {predefinedJunctions.map(junction => (
                  <option key={junction} value={junction}>
                    {junction}
                  </option>
                ))}
              </select>
            </div>

            <button 
              onClick={handleProceed} 
              className="main-btn" 
              style={{ width: '100%' }}
              disabled={!selectedJunction}
            >
              ➡️ Proceed to Dashboard
            </button>
          </div>

          <div className="back-link">
            <button onClick={() => navigate('login')}>
              ⬅️ Back to Login
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default SelectJunctionPage; 