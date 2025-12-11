import React, { useEffect, useState } from 'react'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Admin from './pages/Admin'

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [userRole, setUserRole] = useState('')
  const [userEmail, setUserEmail] = useState('')

  useEffect(() => {
    const value = localStorage.getItem('agrochat_logged_in') === 'true'
    const role = localStorage.getItem('agrochat_role') || ''
    const email = localStorage.getItem('agrochat_email') || ''
    setLoggedIn(value)
    setUserRole(role)
    setUserEmail(email)
  }, [])

  function getUsers() {
    const usersJson = localStorage.getItem('agrochat_users')
    return usersJson ? JSON.parse(usersJson) : []
  }

  function saveUsers(users) {
    localStorage.setItem('agrochat_users', JSON.stringify(users))
  }

  function onRegister(email, password, role, onError) {
    const users = getUsers()
    
    // Check if user already exists
    if (users.find(u => u.email === email)) {
      onError('Email already registered')
      return
    }

    // Create new user
    const newUser = {
      email,
      password, // In a real app, this should be hashed
      role: role || 'user'
    }

    users.push(newUser)
    saveUsers(users)

    // Auto-login after registration
    localStorage.setItem('agrochat_logged_in', 'true')
    localStorage.setItem('agrochat_email', email)
    localStorage.setItem('agrochat_role', newUser.role)
    setLoggedIn(true)
    setUserRole(newUser.role)
    setUserEmail(email)
  }

  function onLogin(email, password, role, onError) {
    const users = getUsers()
    const user = users.find(u => u.email === email && u.password === password)

    if (!user) {
      onError('Invalid email or password')
      return false
    }

    // Verify the selected role matches the user's role
    if (user.role !== role) {
      onError(`Invalid role. This account is registered as ${user.role}`)
      return false
    }

    localStorage.setItem('agrochat_logged_in', 'true')
    localStorage.setItem('agrochat_email', email)
    localStorage.setItem('agrochat_role', user.role)
    setLoggedIn(true)
    setUserRole(user.role)
    setUserEmail(email)
    return true
  }

  function onLogout() {
    localStorage.removeItem('agrochat_logged_in')
    localStorage.removeItem('agrochat_email')
    localStorage.removeItem('agrochat_role')
    setLoggedIn(false)
    setUserRole('')
    setUserEmail('')
  }

  function getViewComponent() {
    if (!loggedIn) {
      return (
        <div className="login-page-wrapper">
          <Login onLogin={onLogin} onRegister={onRegister} />
        </div>
      )
    }
    if (userRole === 'admin') return <Admin onLogout={onLogout} />
    return <Chat onLogout={onLogout} userEmail={userEmail} />
  }

  return getViewComponent()
}
