import React from 'react';

const Header = ({ title = "Society For Cyberabad Security Council", showSwitchButton = false, onSwitchJunction }) => (
  <div className="header">
    <div className="header-content">
      <h1 className="org-name">{title}</h1>
      {showSwitchButton && (
        <button onClick={onSwitchJunction} className="main-btn" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
          🔄 Switch Junction
        </button>
      )}
    </div>
  </div>
);

export default Header; 