import React from 'react';
import Header from './Header';

const HomePage = ({ navigate }) => (
  <>
    <Header />
    <div className="container">
      <div className="card home-card">
        <div className="logo-container">
          <div className="logo">🚦</div>
        </div>
        <h1>Smart Traffic Management System</h1>
        <p className="subtitle">Smart traffic management for a better tomorrow</p>
        
        <div className="features-grid">
          <div className="feature-item">
            <div style={{ fontSize: '2.5rem', color: '#3498db', marginBottom: '1rem' }}>🚦</div>
            <h3>Smart Signals</h3>
            <p>AI-powered traffic signal control</p>
          </div>
          <div className="feature-item">
            <div style={{ fontSize: '2.5rem', color: '#3498db', marginBottom: '1rem' }}>📹</div>
            <h3>Live Monitoring</h3>
            <p>Real-time traffic surveillance</p>
          </div>
          <div className="feature-item">
            <div style={{ fontSize: '2.5rem', color: '#3498db', marginBottom: '1rem' }}>📊</div>
            <h3>Analytics</h3>
            <p>Advanced traffic analysis</p>
          </div>
          <div className="feature-item">
            <div style={{ fontSize: '2.5rem', color: '#3498db', marginBottom: '1rem' }}>🛡️</div>
            <h3>Security</h3>
            <p>Enhanced public safety</p>
          </div>
        </div>

        <div className="button-group">
          <button onClick={() => navigate('login')} className="main-btn">
            🔑 Login
          </button>
          <button onClick={() => navigate('signup')} className="main-btn secondary">
            ✨ Sign Up
          </button>
        </div>
      </div>
    </div>
  </>
);

export default HomePage;