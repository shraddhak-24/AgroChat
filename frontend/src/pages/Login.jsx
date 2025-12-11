import React, { useState, useEffect, useRef } from 'react'

export default function Login({ onLogin, onRegister }) {
  const [isRegisterMode, setIsRegisterMode] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState('user')
  const [error, setError] = useState('')
  const [showSaveCredentials, setShowSaveCredentials] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [savedCredentials, setSavedCredentials] = useState([])
  const [filteredSuggestions, setFilteredSuggestions] = useState([])
  const suggestionsRef = useRef(null)
  const emailInputRef = useRef(null)

  useEffect(() => {
    loadSavedCredentials()
  }, [])

  useEffect(() => {
    if (email.trim()) {
      const filtered = savedCredentials.filter(cred => 
        cred.email.toLowerCase().includes(email.toLowerCase())
      )
      setFilteredSuggestions(filtered)
      setShowSuggestions(filtered.length > 0)
    } else {
      setFilteredSuggestions([])
      setShowSuggestions(false)
    }
  }, [email, savedCredentials])

  useEffect(() => {
    function handleClickOutside(event) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target) && 
          emailInputRef.current && !emailInputRef.current.contains(event.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function loadSavedCredentials() {
    const saved = localStorage.getItem('agrochat_saved_credentials')
    if (saved) {
      setSavedCredentials(JSON.parse(saved))
    }
  }

  function saveCredential(email, password, role) {
    const credentials = [...savedCredentials]
    const existingIndex = credentials.findIndex(c => c.email === email)
    
    const newCredential = { email, password, role, lastUsed: Date.now() }
    
    if (existingIndex >= 0) {
      credentials[existingIndex] = newCredential
    } else {
      credentials.push(newCredential)
    }
    
    localStorage.setItem('agrochat_saved_credentials', JSON.stringify(credentials))
    setSavedCredentials(credentials)
    setShowSaveCredentials(false)
  }

  function selectSuggestion(cred) {
    setEmail(cred.email)
    setPassword(cred.password)
    setRole(cred.role)
    setShowSuggestions(false)
  }

  function removeCredential(email, e) {
    e.stopPropagation()
    const updated = savedCredentials.filter(c => c.email !== email)
    localStorage.setItem('agrochat_saved_credentials', JSON.stringify(updated))
    setSavedCredentials(updated)
  }

  function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  function handleSubmit(e) {
    e.preventDefault()
    setError('')

    // Validation
    if (!email.trim() || !password || !role) {
      setError('Please fill in all fields')
      return
    }

    if (!validateEmail(email.trim())) {
      setError('Please enter a valid email address')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    if (isRegisterMode) {
      if (password !== confirmPassword) {
        setError('Passwords do not match')
        return
      }
      onRegister(email.trim(), password, role, setError)
    } else {
      const loginSuccess = onLogin(email.trim(), password, role, setError)
      if (loginSuccess) {
        // Show save credentials popup if not already saved
        const exists = savedCredentials.find(c => c.email === email.trim())
        if (!exists) {
          setShowSaveCredentials(true)
        }
      }
    }
  }

  return (
    <div className="login-container">
      <div className="login-header">
        <img src="/agrochat-logo.jpg" alt="AgroChat logo" className="login-logo" />
        <h1 className="login-title">Welcome to AgroChat</h1>
      </div>

      {error && <div className="error-message show">{error}</div>}

      <form className="login-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="role" className="form-label">Role</label>
          <select 
            id="role" 
            className="form-input form-select" 
            value={role} 
            onChange={e => setRole(e.target.value)} 
            required
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        <div className="form-group" style={{ position: 'relative' }}>
          <label htmlFor="email" className="form-label">Email</label>
          <input 
            ref={emailInputRef}
            id="email" 
            type="email" 
            className="form-input" 
            value={email} 
            onChange={e => setEmail(e.target.value)}
            onFocus={() => email.trim() && filteredSuggestions.length > 0 && setShowSuggestions(true)}
            placeholder="Enter your email" 
            required 
          />
          {showSuggestions && filteredSuggestions.length > 0 && (
            <div ref={suggestionsRef} className="suggestions-dropdown">
              {filteredSuggestions.map((cred, idx) => (
                <div key={idx} className="suggestion-item" onClick={() => selectSuggestion(cred)}>
                  <div className="suggestion-info">
                    <div className="suggestion-email">{cred.email}</div>
                    <div className="suggestion-role">Role: {cred.role}</div>
                  </div>
                  <button 
                    className="suggestion-remove" 
                    onClick={(e) => removeCredential(cred.email, e)}
                    title="Remove saved credential"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="password" className="form-label">Password</label>
          <input 
            id="password" 
            type="password" 
            className="form-input" 
            value={password} 
            onChange={e => setPassword(e.target.value)} 
            placeholder="Enter your password" 
            required 
          />
        </div>

        {isRegisterMode && (
          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
            <input 
              id="confirmPassword" 
              type="password" 
              className="form-input" 
              value={confirmPassword} 
              onChange={e => setConfirmPassword(e.target.value)} 
              placeholder="Confirm your password" 
              required 
            />
          </div>
        )}

        <button type="submit" className="login-button">
          {isRegisterMode ? 'Register' : 'Sign In'}
        </button>
      </form>

      <div className="forgot-password">
        {isRegisterMode ? (
          <span>
            Already have an account?{' '}
            <a href="#" onClick={e => { e.preventDefault(); setIsRegisterMode(false); setError(''); setConfirmPassword(''); setRole('user') }}>
              Sign In
            </a>
          </span>
        ) : (
          <>
            <a href="#" onClick={e => { e.preventDefault(); setIsRegisterMode(true); setError(''); setRole('user') }}>
              Don't have an account? Register
            </a>
            <br />
            <a href="#" onClick={e => { e.preventDefault(); alert('Password reset feature coming soon!') }}>
              Forgot password?
            </a>
          </>
        )}
      </div>

      {showSaveCredentials && (
        <div className="modal-overlay" onClick={() => setShowSaveCredentials(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Save Credentials?</h3>
            <p>Would you like to save your login credentials for faster access next time?</p>
            <div className="modal-buttons">
              <button 
                className="modal-btn-primary" 
                onClick={() => saveCredential(email.trim(), password, role)}
              >
                Save
              </button>
              <button 
                className="modal-btn-secondary" 
                onClick={() => setShowSaveCredentials(false)}
              >
                Don't Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
