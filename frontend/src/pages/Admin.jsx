import React from 'react'

export default function Admin({ onLogout }) {
  return (
    <div id="app-wrapper">
      <header className="top-bar">
        <div className="brand">
          <img src="/agrochat-logo.jpg" alt="AgroChat logo" className="brand-logo" />
          <span className="brand-name">AgroChat - Admin Panel</span>
        </div>
        <button className="logout-btn" onClick={() => { if (confirm('Are you sure you want to logout?')) onLogout() }}>Logout</button>
      </header>

      <div className="admin-container">
        <div className="admin-content">
          <h1>Admin Dashboard</h1>
          <p>Welcome to the Admin Panel</p>
          <p>This area is reserved for administrative functions.</p>
        </div>
      </div>
    </div>
  )
}



