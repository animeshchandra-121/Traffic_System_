import React, { useState } from 'react';
import Header from './Header';

const LoginPage = ({ navigate }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('isLoading before:', isLoading)
    setError('');
    setIsLoading(true);
    setTimeout(() => {
      console.log('Navigating to select-junction');
      navigate('select-junction');
      setIsLoading(false);
    }, 500);
  };

  return (
    <>
      <Header />
      <div className="container">
        <div className="card">
          <div className="logo-container">
            <div className="logo" style={{ maxWidth: '150px', width: '100px', height: '100px', fontSize: '1.5rem' }}>🚦</div>
          </div>
          <h1>Welcome Back</h1>
          <p className="subtitle">Please login to access the system</p>
          
          {error && <div className="error-message">{error}</div>}
          
          <div style={{ textAlign: 'left' }}>
            <div className="form-group">
              <label htmlFor="username">
                👤 Username
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="Enter your username"
                disabled={isLoading}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">
                🔒 Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                disabled={isLoading}
                required
              />
            </div>
            
            <button 
              onClick={handleSubmit} 
              className="main-btn" 
              style={{ width: '100%' }}
              disabled={isLoading}
            >
              {isLoading ? 'Logging in...' : '🔑 Login'}
            </button>
          </div>

          <div className="back-link">
            <button 
              onClick={() => navigate('home')} 
              className="main-btn" 
              style={{ 
                background: 'transparent', 
                color: '#3498db',
                border: '2px solid #3498db',
                boxShadow: 'none',
                marginTop: '1rem'
              }}
              disabled={isLoading}
            >
              ⬅️ Back to Home
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default LoginPage; 