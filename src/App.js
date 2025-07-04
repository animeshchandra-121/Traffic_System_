import React, { useState } from 'react';
import LoginPage from './components/LoginPage';
import SelectJunctionPage from './components/SelectJunctionPage';
import DashboardPage from './components/DashboardPage';
import './styles/App.css';

console.log("App rendered");

const App = () => {
  const [currentPage, setCurrentPage] = useState('login');

  const [selectedJunction, setSelectedJunction] = useState('');

  const navigate = (page, junction = '') => {
    setCurrentPage(page);
    if (junction) setSelectedJunction(junction);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'login':
        return <LoginPage navigate={navigate} />;
      case 'select-junction':
        return <SelectJunctionPage navigate={navigate} />
      case 'dashboard':
        return <DashboardPage navigate={navigate} />;
      default:
        return <LoginPage navigate={navigate} />;
    }
  };

  return (
    <div className="app">
      {renderPage()}
    </div>
  );
};

export default App; 
