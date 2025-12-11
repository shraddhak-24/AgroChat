import React, { useEffect, useRef, useState } from 'react'

// Backend API base URL
const BACKEND_URL = 'http://127.0.0.1:8005'


async function fetchWeatherByCoords(lat, lon) {
  try {
    const res = await fetch(`${BACKEND_URL}/weather_coords?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)
    if (!res.ok) return null
    return await res.json()
  } catch (e) {
    console.error('Weather by coords error:', e)
    return null
  }
}


// Convert dataURL to blob
function dataURLtoBlob(dataURL) {
  const arr = dataURL.split(',')
  const mime = arr[0].match(/:(.*?);/)[1]
  const bstr = atob(arr[1])
  let n = bstr.length
  const u8arr = new Uint8Array(n)
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n)
  }
  return new Blob([u8arr], { type: mime })
}

// Call backend API to analyze image or text
async function callBackendAPI(images, text, context) {
  try {
    // 1️⃣ Image flow → /analyze
    if (images && images.length > 0) {
      const formData = new FormData()
      // Convert dataURL to blob and append
      for (const img of images) {
        const blob = dataURLtoBlob(img.url)
        formData.append('image', blob, img.name)  // Changed from 'file' to 'image'
      }
      
      // Add question as query parameter
      const question = (text || '').trim() || "What treatment do you recommend?"
      const url = new URL(`${BACKEND_URL}/analyze`)
      url.searchParams.append('question', question)

      // Attach optional conversation context (JSON string) as a form field
      if (context) {
        try {
          const ctxJson = typeof context === 'string' ? context : JSON.stringify(context)
          formData.append('context', ctxJson)
        } catch (e) {
          console.warn('Failed to serialize context for backend:', e)
        }
      }
      
      const res = await fetch(url.toString(), {
        method: 'POST',
        body: formData
      })
      
      if (res.ok) {
        const data = await res.json()
        return `Disease: ${data.disease}\nConfidence: ${data.confidence}%\n\nAdvice: ${data.advice}`
      } else {
        const errText = await res.text()
        return `Error analyzing image: ${errText || 'Unknown error'}`
      }

    // 2️⃣ Text-only flow → /chat
    } else if (text && text.trim()) {
      const payload = {
        question: text.trim(),
        context: context || []  // last few messages from this conversation
      }

      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        const data = await res.json()
        // Expecting backend to return { answer: "..." }
        if (data && (data.answer || data.response)) {
          return data.answer || data.response
        }
        // Fallback: show whatever the backend sent
        return JSON.stringify(data)
      } else {
        const errText = await res.text()
        return `Error from chat endpoint: ${errText || 'Unknown error'}`
      }

    // 3️⃣ Nothing provided
    } else {
      return 'Please provide text or upload an image.'
    }
  } catch (error) {
    console.error('Backend API error:', error)
    // Try one quick retry (network glitches)
    try {
      await new Promise(r => setTimeout(r, 500))
      const retryRes = await fetch(`${BACKEND_URL}/health`)
      if (retryRes.ok) {
        return `Error: ${error.message}. Backend appears reachable now; try again.`
      }
    } catch(_) {}
    return `Error: ${error.message}. Make sure the backend is running at ${BACKEND_URL}`
  }
}

function generateConversationTitle(firstMessage) {
  const words = (firstMessage || '').split(' ').slice(0, 4)
  return words.join(' ') + ((firstMessage || '').split(' ').length > 4 ? '...' : '') || 'New Conversation'
}

export default function Chat({ onLogout, userEmail }) {
  const [conversations, setConversations] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [sidebarVisible, setSidebarVisible] = useState(true)
  // Right-hand conversations panel removed.
  const [attachedFiles, setAttachedFiles] = useState([])
  const [text, setText] = useState('')
  const [imageCategory, setImageCategory] = useState('')
  const [selectedImage, setSelectedImage] = useState(null)
  const [isTyping, setIsTyping] = useState(false)
  const [backendAvailable, setBackendAvailable] = useState(true)
  const messagesRef = useRef(null)

  useEffect(() => {
    // Try loading conversations from backend first, fallback to localStorage
    const storageKey = `agrochat_conversations_${userEmail || 'local'}`

    let mounted = true
    async function loadConversations() {
      // Attempt server-side load
      try {
        const res = await fetch(`${BACKEND_URL}/conversations`)
        if (res.ok) {
          const data = await res.json()
          if (mounted && data && Array.isArray(data.conversations) && data.conversations.length > 0) {
            setConversations(data.conversations)
            setCurrentConversationId(data.conversations[0].id)
            return
          }
        }
      } catch (e) {
        // ignore, fall back to localStorage
      }

      // Local fallback
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        try {
          setConversations(JSON.parse(saved))
        } catch (e) {
          console.error('Failed to parse saved conversations:', e)
        }
      } else {
        // create a default conversation with an initial bot greeting
        const defaultConv = {
          id: Date.now().toString(),
          title: 'Welcome',
          messages: [{ text: 'Hello! How can I help with your agriculture questions today?', type: 'bot', timestamp: Date.now() }],
          lastMessage: Date.now(),
          createdAt: Date.now()
        }
        setConversations([defaultConv])
        setCurrentConversationId(defaultConv.id)
      }
    }

    loadConversations()

    const savedLeft = localStorage.getItem('agrochat_sidebar_visible')
    if (savedLeft !== null) setSidebarVisible(savedLeft === 'true')

    return () => { mounted = false }
  }, [userEmail])

  // Check backend health on mount and when backend URL changes
  useEffect(() => {
    let mounted = true
    async function checkHealth() {
      try {
        const res = await fetch(`${BACKEND_URL}/health`)
        if (!mounted) return
        setBackendAvailable(res.ok)
      } catch (e) {
        if (!mounted) return
        console.warn('Backend health check failed', e)
        setBackendAvailable(false)
      }
    }
    checkHealth()
    const id = setInterval(checkHealth, 15000) // recheck every 15s
    return () => { mounted = false; clearInterval(id) }
  }, [])

  // On mount, try to get browser geolocation and fetch local weather automatically
  useEffect(() => {
    if (!('geolocation' in navigator)) return

    let mounted = true

    function success(pos) {
      if (!mounted) return
      const { latitude, longitude } = pos.coords
      ;(async () => {
        const weather = await fetchWeatherByCoords(latitude, longitude)
        if (!weather || !mounted) return

        const summary = `Local weather: ${weather.description || 'N/A'}, ${weather.temperature_c}°C`
        const details = `Location: ${weather.location || ''}\nTemperature: ${weather.temperature_c}°C\nFeels like: ${weather.feels_like_c}°C\nHumidity: ${weather.humidity}%\nWind: ${weather.wind_m_s} m/s`

        // If there's an active conversation, post; otherwise create one with message
        if (currentConv && currentConv.id) {
          addMessage(currentConv.id, { text: summary, summary: summary, details: details, type: 'bot', timestamp: Date.now() })
        } else {
          const newConv = {
            id: Date.now().toString(),
            title: 'Local Weather',
            messages: [{ text: summary, summary: summary, details: details, type: 'bot', timestamp: Date.now() }],
            lastMessage: Date.now(),
            createdAt: Date.now()
          }
          setConversations(prev => [newConv, ...prev])
          setCurrentConversationId(newConv.id)
        }
      })()
    }

    function fail(err) {
      // silently ignore geolocation failures (user denied or timed out)
      console.warn('Geolocation failed or denied:', err)
    }

    navigator.geolocation.getCurrentPosition(success, fail, { timeout: 10000 })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    const storageKey = `agrochat_conversations_${userEmail || 'local'}`
    try {
      localStorage.setItem(storageKey, JSON.stringify(conversations))
    } catch (e) {
      console.error('Failed to save conversations:', e)
    }
  }, [conversations, userEmail])

  // Sync a single conversation to the backend
  async function syncConversationToServer(conv) {
    if (!conv || !conv.id) return
    try {
      await fetch(`${BACKEND_URL}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conv)
      })
    } catch (e) {
      // ignore network errors; conversation remains in localStorage
    }
  }

  // Whenever conversations change, attempt to sync them to the server in background
  useEffect(() => {
    if (!conversations || conversations.length === 0) return
    // Fire-and-forget: sync latest conversations
    for (const conv of conversations) {
      syncConversationToServer(conv)
    }
  }, [conversations])

  // Get current conversation with latest state
  const currentConv = conversations.find(c => c.id === currentConversationId) || conversations[0]

  // Auto-scroll when conversation changes or new messages are added
  useEffect(() => {
    const timer = setTimeout(() => scrollToBottom(), 50)
    return () => clearTimeout(timer)
  }, [currentConversationId, currentConv?.messages?.length])

  useEffect(() => {
    if (!currentConversationId && conversations.length === 0) startNewConversation()
  }, [conversations, currentConversationId])

  function startNewConversation() {
    const newConv = { 
      id: Date.now().toString(), 
      title: 'New Conversation', 
      messages: [], 
      lastMessage: Date.now(),
      createdAt: Date.now()
    }
    setConversations(prev => [newConv, ...prev])
    setCurrentConversationId(newConv.id)
    setText('')
    setAttachedFiles([])
    setImageCategory('')
  }

  function groupConversationsByDate(convs) {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const weekAgo = new Date(today)
    weekAgo.setDate(weekAgo.getDate() - 7)

    const groups = {
      today: [],
      yesterday: [],
      thisWeek: [],
      thisMonth: [],
      older: []
    }

    convs.forEach(conv => {
      const convDate = new Date(conv.lastMessage || conv.createdAt || 0)
      
      if (convDate >= today) {
        groups.today.push(conv)
      } else if (convDate >= yesterday) {
        groups.yesterday.push(conv)
      } else if (convDate >= weekAgo) {
        groups.thisWeek.push(conv)
      } else {
        const monthAgo = new Date(today)
        monthAgo.setMonth(monthAgo.getMonth() - 1)
        if (convDate >= monthAgo) {
          groups.thisMonth.push(conv)
        } else {
          groups.older.push(conv)
        }
      }
    })

    return groups
  }

  function formatConversationGroupName(groupName) {
    const names = {
      today: 'Today',
      yesterday: 'Yesterday',
      thisWeek: 'Previous 7 Days',
      thisMonth: 'Previous 30 Days',
      older: 'Older'
    }
    return names[groupName] || groupName
  }

  function saveConversation(update) {
    setConversations(prev => prev.map(c => (c.id === update.id ? update : c)))
  }

  function addMessage(convId, message) {
    setConversations(prev => {
      const conv = prev.find(c => c.id === convId)
      if (!conv) return prev
      const updated = { ...conv, messages: [...conv.messages, message], lastMessage: Date.now() }
      return prev.map(c => (c.id === convId ? updated : c))
    })
    setTimeout(() => scrollToBottom(), 100)
  }

  function scrollToBottom() {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight
    }
  }

  function fileToDataURL(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  async function handleSubmit(e) {
    e && e.preventDefault()
    if (!text.trim() && attachedFiles.length === 0) return
    
    // If images are attached, require category selection
    const hasImages = attachedFiles.some(f => f.type.startsWith('image/'))
    if (hasImages && !imageCategory) {
      alert('Please select a category (Insect or Disease) for the image(s)')
      return
    }
    
    let conv = conversations.find(c => c.id === currentConversationId)
    if (!conv) {
      const newConv = { 
        id: Date.now().toString(), 
        title: 'New Conversation', 
        messages: [], 
        lastMessage: Date.now(),
        createdAt: Date.now()
      }
      setConversations(prev => [newConv, ...prev])
      setCurrentConversationId(newConv.id)
      conv = newConv
    }
    if (conv.messages.length === 0) {
      conv.title = generateConversationTitle(text || 'File attachment')
      saveConversation(conv)
    }

    // Convert image files to data URLs and prepare message
    const images = []
    const otherFiles = []
    
    for (const file of attachedFiles) {
      if (file.type.startsWith('image/')) {
        try {
          const dataURL = await fileToDataURL(file)
          images.push({
            url: dataURL,
            name: file.name,
            category: imageCategory
          })
        } catch (error) {
          console.error('Error converting image:', error)
          otherFiles.push(file.name)
        }
      } else {
        otherFiles.push(file.name)
      }
    }

    const messageText = text.trim() || ''
    const fileNamesText = otherFiles.length > 0 ? `\n[Attached: ${otherFiles.join(', ')}]` : ''
    
    addMessage(conv.id, { 
      text: messageText + fileNamesText, 
      type: 'user', 
      timestamp: Date.now(),
      images: images.length > 0 ? images : undefined
    })
    
    setText('')
    setAttachedFiles([])
    setImageCategory('')

    // Prevent sending if backend unavailable
    if (!backendAvailable) {
      addMessage(conv.id, { text: `Error: Failed to reach backend at ${BACKEND_URL}. Please ensure the backend is running.`, type: 'bot', timestamp: Date.now() })
      return
    }

    // Show typing indicator
    setIsTyping(true)
    // Build a small context (last 6 messages text) to send for follow-ups
    const recent = (conv.messages || []).slice(-6).map(m => ({ type: m.type, text: m.text }))
    // Call backend API with context
    // WEATHER DETECTION
const lower = messageText.toLowerCase();
  if (
    lower.includes("weather") ||
    lower.includes("temperature") ||
    lower.includes("climate")
  ) {
    // extract possible city
    let city = messageText
      .replace(/weather|temperature|climate|in|today|'s/gi, "")
      .trim();

    if (!city) city = "Hyderabad"; // fallback

    // Inline fetch to /weather (replaces removed helper)
    let weather = null
    try {
      const res = await fetch(`${BACKEND_URL}/weather?query=${encodeURIComponent(city)}`)
      if (res.ok) weather = await res.json()
    } catch (e) {
      console.error('Weather fetch failed:', e)
      weather = null
    }

    setIsTyping(false)

    if (weather && weather.success) {
      const reply = `🌤 Weather in ${weather.city}\nTemperature: ${weather.temperature}°C\nFeels Like: ${weather.feels_like}°C\nHumidity: ${weather.humidity}%\nCondition: ${weather.description}`

      addMessage(conv.id, {
        text: reply,
        summary: reply.split("\n")[0],
        details: reply.split("\n").slice(1).join("\n"),
        type: "bot",
        timestamp: Date.now(),
      })

      return
    } else {
      addMessage(conv.id, {
        text: `Could not fetch weather for "${city}".`,
        type: "bot",
        timestamp: Date.now(),
      })
      return
    }
  }


    const botReply = await callBackendAPI(images, messageText, recent)
    setIsTyping(false)

    // Create summary + details for nicer UX
    let summary = ''
    let details = ''
    if (botReply) {
      // Prefer splitting by double newline or by first sentence
      if (botReply.includes('\n\n')) {
        const parts = botReply.split('\n\n')
        summary = parts[0].trim()
        details = parts.slice(1).join('\n\n').trim()
      } else {
        // fallback: first 140 chars as summary
        summary = botReply.split('\n')[0].trim()
        details = botReply.split('\n').slice(1).join('\n').trim()
        if (!details && summary.length > 140) {
          details = summary.slice(140).trim()
          summary = summary.slice(0, 140).trim() + '...'
        }
      }
    }

    addMessage(conv.id, { text: botReply, summary: summary, details: details, type: 'bot', timestamp: Date.now() })
  }

  function selectConversation(id) {
    setCurrentConversationId(id)
  }

  function toggleSidebar() {
    setSidebarVisible(v => { const next = !v; localStorage.setItem('agrochat_sidebar_visible', next); return next })
  }

  // right sidebar toggling removed

  function attachFiles(files) {
    const list = Array.from(files)
    setAttachedFiles(prev => {
      const merged = [...prev]
      list.forEach(f => {
        if (!merged.find(m => m.name === f.name && m.size === f.size)) merged.push(f)
      })
      return merged
    })
    // Reset category when new files are added
    const hasImages = list.some(f => f.type.startsWith('image/'))
    if (hasImages) {
      setImageCategory('')
    }
  }

  function removeAttachedFile(name, size) {
    setAttachedFiles(prev => {
      const remaining = prev.filter(f => !(f.name === name && f.size === size))
      // Check if there are still images, if not, reset category
      const stillHasImages = remaining.some(f => f.type.startsWith('image/'))
      if (!stillHasImages) {
        setImageCategory('')
      }
      return remaining
    })
  }

  function sendQuick(q) {
    setText(q)
    // use setTimeout to behave like pressing send
    setTimeout(() => handleSubmit(), 50)
  }

  return (
    <div id="app-wrapper">
      <header className="top-bar">
        <div className="brand">
          <img src="/agrochat-logo.jpg" alt="AgroChat logo" className="brand-logo" />
          <span className="brand-name">AgroChat</span>
        </div>
        <button className="logout-btn" onClick={() => { if (confirm('Are you sure you want to logout?')) onLogout() }}>Logout</button>
      </header>

      <div className={`app-body ${!sidebarVisible ? 'sidebar-hidden' : ''}`}>
        <aside className={`sidebar ${!sidebarVisible ? 'hidden' : ''}`}>
          <div className="sidebar-header">
            <h3>Conversations</h3>
            <button className="sidebar-close" onClick={toggleSidebar}>×</button>
          </div>
          <button className="new-chat-button" onClick={startNewConversation}>
            <span className="new-chat-icon">+</span>
            New Chat
          </button>
          <div className="conversation-list-container">
            {conversations.length === 0 ? (
              <div className="empty-conversations">No previous conversations</div>
            ) : (
              (() => {
                const sortedConvs = conversations.slice().sort((a, b) => (b.lastMessage || b.createdAt || 0) - (a.lastMessage || a.createdAt || 0))
                const grouped = groupConversationsByDate(sortedConvs)
                const groupOrder = ['today', 'yesterday', 'thisWeek', 'thisMonth', 'older']
                
                return groupOrder.map(groupName => {
                  const groupConvs = grouped[groupName]
                  if (groupConvs.length === 0) return null
                  
                  return (
                    <div key={groupName} className="conversation-group">
                      <div className="conversation-group-header">{formatConversationGroupName(groupName)}</div>
                      <ul className="conversation-list">
                        {groupConvs.map(conv => (
                          <li 
                            key={conv.id} 
                            className={`conversation ${conv.id === currentConversationId ? 'active' : ''}`} 
                            onClick={() => selectConversation(conv.id)}
                          >
                            {conv.title}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )
                })
              })()
            )}
          </div>
        </aside>

        <main className="chat-panel">
          <div className="chat-header">
            <button className="sidebar-toggle-inner" onClick={toggleSidebar} title="Conversations">
              <span className="toggle-icon">☰</span>
              <span className="toggle-text">Conversations</span>
              <div className="tooltip">Open sidebar</div>
            </button>
          </div>

          <div className="chat-messages" ref={messagesRef}>
            {(currentConv?.messages || []).map((m, i) => (
              <div key={i} className={`msg ${m.type}`}>
                {m.images && m.images.length > 0 && (
                  <div className="msg-images">
                    {m.images.map((img, idx) => (
                      <div key={idx} className="msg-image-container">
                        <img 
                          src={img.url} 
                          alt={img.name} 
                          className="msg-image" 
                          onClick={() => setSelectedImage(img.url)}
                        />
                        {img.category && <span className="image-category-badge">{img.category}</span>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Bot message: show summary and expandable details */}
                {m.type === 'bot' ? (
                  <div className="bot-reply">
                    {m.summary ? (
                      <p style={{ whiteSpace: 'pre-wrap', fontWeight: 600 }}>{m.summary}</p>
                    ) : (
                      m.text && <p style={{ whiteSpace: 'pre-wrap' }}>{m.text}</p>
                    )}

                    {m.details ? (
                      <details className="reply-details">
                        <summary>Show details</summary>
                        <pre style={{ whiteSpace: 'pre-wrap' }}>{m.details}</pre>
                      </details>
                    ) : null}
                  </div>
                ) : (
                  // user message
                  m.text && <p style={{ whiteSpace: 'pre-wrap' }}>{m.text}</p>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="msg bot typing-indicator">
                <div className="typing-dots">Assistant is typing<span className="dots">...</span></div>
              </div>
            )}
          </div>

          {selectedImage && (
            <div className="image-modal" onClick={() => setSelectedImage(null)}>
              <div className="image-modal-content" onClick={(e) => e.stopPropagation()}>
                <button className="image-modal-close" onClick={() => setSelectedImage(null)}>×</button>
                <img src={selectedImage} alt="Full size" className="image-modal-image" />
              </div>
            </div>
          )}

          <div className="quick-actions">
            <button onClick={() => sendQuick('Check crop disease')}>Check crop disease</button>
            <button onClick={() => sendQuick('Recommend fertilizer')}>Recommend fertilizer</button>
            <button onClick={() => sendQuick("Today's weather advice")}>Today's weather advice</button>
          </div>

          {attachedFiles.some(f => f.type.startsWith('image/')) && (
            <div className="image-category-selector">
              <label htmlFor="image-category" className="category-label">Image Category:</label>
              <select 
                id="image-category" 
                className="category-select" 
                value={imageCategory} 
                onChange={e => setImageCategory(e.target.value)}
              >
                <option value="">Select category...</option>
                <option value="Insect">Insect</option>
                <option value="Disease">Disease</option>
              </select>
            </div>
          )}
          <form className="chat-input" onSubmit={handleSubmit}>
            <input style={{ display: 'none' }} id="file-input" type="file" multiple accept="image/*,.pdf,.doc,.docx,.txt" onChange={e => attachFiles(e.target.files)} />
            <button type="button" className="attach-btn" onClick={() => document.getElementById('file-input').click()}>📎</button>
            <input id="chat-text" value={text} onChange={e => setText(e.target.value)} placeholder="Type your message here..." autoComplete="off" />
            <button type="submit" className="send-btn">➤</button>
          </form>
          <div className="attached-files">
            {attachedFiles.map((f, idx) => (
              <div className="attached-file-item" key={idx}>
                <span className="file-icon">📎</span>
                <span className="file-name" title={f.name}>{f.name}</span>
                <button type="button" className="file-remove" onClick={() => removeAttachedFile(f.name, f.size)}>×</button>
              </div>
            ))}
          </div>
        </main>

        {/* right-side conversations removed */}
      </div>
    </div>
  )
}
