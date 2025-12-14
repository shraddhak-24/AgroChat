import React, { useEffect, useRef, useState } from 'react'

// Backend API base URL
const BACKEND_URL = 'http://127.0.0.1:8000'

async function fetchWeatherByCoords(lat, lon) {
  try {
    const res = await fetch(`${BACKEND_URL}/weather_coords?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

function dataURLtoBlob(dataURL) {
  const arr = dataURL.split(',')
  const mime = arr[0].match(/:(.*?);/)[1]
  const bstr = atob(arr[1])
  let n = bstr.length
  const u8arr = new Uint8Array(n)
  while (n--) u8arr[n] = bstr.charCodeAt(n)
  return new Blob([u8arr], { type: mime })
}

async function callBackendAPI(images, text, context, category) {
  try {
    if (images && images.length > 0) {
      const formData = new FormData()
      for (const img of images) {
        const blob = dataURLtoBlob(img.url)
        formData.append('image', blob, img.name)
      }

      let question = text?.trim() || 'What treatment do you recommend?'
      if (category) {
        question = `[${category}] ${question}`
      }
      
      const url = new URL(`${BACKEND_URL}/analyze`)
      url.searchParams.append('question', question)

      if (context) {
        formData.append('context', JSON.stringify(context))
      }

      const res = await fetch(url.toString(), { method: 'POST', body: formData })
      const data = await res.json()
      
      // Check if this is an insect identification
      if (data.is_insect) {
        return data.advice || 'Insect identification help is being processed...'
      }
      
      // Format response nicely for plant diseases
      const diseaseTitle = data.disease_title || data.disease
      const confidence = data.confidence
      const advice = data.advice || 'No specific advice available.'
      
      // Format with better structure
      let formattedResponse = `🌱 Plant Disease Analysis\n\n`
      formattedResponse += `Disease Detected: ${diseaseTitle}\n`
      formattedResponse += `Confidence: ${confidence}%\n\n`
      formattedResponse += `${advice}`
      
      return formattedResponse
    }

    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, context })
    })

    const data = await res.json()
    return data.answer || JSON.stringify(data)
  } catch (e) {
    return `Error: ${e.message}`
  }
}

function generateConversationTitle(text) {
  const words = (text || '').split(' ').slice(0, 4)
  return words.join(' ') + (words.length >= 4 ? '...' : '')
}

export default function Chat({ onLogout, userEmail }) {
  const [conversations, setConversations] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [attachedFiles, setAttachedFiles] = useState([])
  const [text, setText] = useState('')
  const [imageCategory, setImageCategory] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [expandedImage, setExpandedImage] = useState(null)
  const [deletingConvId, setDeletingConvId] = useState(null)
  const messagesRef = useRef(null)
  const fileInputRef = useRef(null)

  const currentConv = conversations.find(c => c.id === currentConversationId)

  useEffect(() => {
    fetch(`${BACKEND_URL}/conversations`)
      .then(res => res.json())
      .then(data => {
        if (data.conversations?.length) {
          // Filter out empty conversations
          const nonEmpty = data.conversations.filter(c => c.messages && c.messages.length > 0)
          setConversations(nonEmpty)
          if (nonEmpty.length > 0) {
            setCurrentConversationId(nonEmpty[0].id)
          }
        }
      })
      .catch(err => console.error('Failed to load conversations:', err))
  }, [])

  // Auto-scroll to bottom when conversation changes or new messages arrive
  useEffect(() => {
    if (messagesRef.current && currentConv) {
      setTimeout(() => {
        messagesRef.current.scrollTop = messagesRef.current.scrollHeight
      }, 100)
    }
  }, [currentConv?.messages?.length, currentConversationId])

  // Save conversation to backend
  async function saveConversation(conv) {
    // Only save if conversation has messages
    if (!conv.messages || conv.messages.length === 0) {
      return
    }

    try {
      const res = await fetch(`${BACKEND_URL}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conv)
      })
      const data = await res.json()
      if (!data.success) {
        console.warn('Failed to save conversation:', data.error)
      }
    } catch (err) {
      console.error('Error saving conversation:', err)
    }
  }

  // Delete conversation
  async function deleteConversation(convId, e) {
    e?.stopPropagation()
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return
    }

    setDeletingConvId(convId)
    try {
      const res = await fetch(`${BACKEND_URL}/conversations/${convId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        setConversations(prev => {
          const updated = prev.filter(c => c.id !== convId)
          if (currentConversationId === convId && updated.length > 0) {
            setCurrentConversationId(updated[0].id)
          } else if (updated.length === 0) {
            setCurrentConversationId(null)
          }
          return updated
        })
      }
    } catch (err) {
      console.error('Error deleting conversation:', err)
      alert('Failed to delete conversation')
    } finally {
      setDeletingConvId(null)
    }
  }

  function startNewConversation() {
    // Don't create new if current is empty
    if (currentConv && currentConv.messages.length === 0) {
      return
    }

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

  function addMessage(convId, msg, onComplete) {
    setConversations(prev => {
      const updated = prev.map(c =>
        c.id === convId
          ? { ...c, messages: [...c.messages, msg], lastMessage: Date.now() }
          : c
      )
      // Call onComplete with updated conversation if provided
      if (onComplete) {
        const updatedConv = updated.find(c => c.id === convId)
        if (updatedConv) {
          setTimeout(() => onComplete(updatedConv), 0)
        }
      }
      return updated
    })
    // Auto-scroll to bottom when new message is added
    setTimeout(() => {
      if (messagesRef.current) {
        messagesRef.current.scrollTop = messagesRef.current.scrollHeight
      }
    }, 100)
  }

  // Auto-scroll when conversation changes or messages update
  useEffect(() => {
    if (messagesRef.current && currentConv) {
      setTimeout(() => {
        messagesRef.current.scrollTop = messagesRef.current.scrollHeight
      }, 100)
    }
  }, [currentConv?.messages?.length, currentConversationId, isTyping])

  function handleFileSelect(e) {
    const files = Array.from(e.target.files || [])
    files.forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (event) => {
          setAttachedFiles(prev => [...prev, {
            url: event.target.result,
            name: file.name,
            file: file
          }])
        }
        reader.readAsDataURL(file)
      }
    })
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function removeFile(index) {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
  }

  async function handleSuggestion(suggestion) {
    // Don't auto-fill, just focus the input and show a placeholder hint
    const inputField = document.querySelector('.chat-input-field')
    if (inputField) {
      inputField.focus()
    }
    
    if (suggestion === 'weather') {
      // Just set a placeholder hint, don't auto-fill
      const input = document.querySelector('.chat-input-field')
      if (input) {
        input.placeholder = "Try: 'What's the weather in Chennai?' or 'Weather in Mumbai'"
      }
    } else if (suggestion === 'disease') {
      // Set category but don't auto-fill text
      setImageCategory('disease')
      const input = document.querySelector('.chat-input-field')
      if (input) {
        input.placeholder = "Upload an image and describe the plant disease symptoms..."
      }
    } else if (suggestion === 'insect') {
      // Set category but don't auto-fill text
      setImageCategory('insect')
      const input = document.querySelector('.chat-input-field')
      if (input) {
        input.placeholder = "Upload an image and describe the insect you want to identify..."
      }
    }
  }

  async function handleSubmit(e) {
    e?.preventDefault()
    if (!text.trim() && attachedFiles.length === 0) return

    let conv = currentConv
    if (!conv) {
      startNewConversation()
      conv = conversations.find(c => c.id === currentConversationId)
      if (!conv) return
    }

    // Prepare user message with images
    const userMessage = {
      text: text || (attachedFiles.length > 0 ? (imageCategory ? `[${imageCategory}] Image analysis` : 'Image analysis') : ''),
      type: 'user',
      timestamp: Date.now(),
      images: attachedFiles.map(f => ({ url: f.url, name: f.name })),
      category: imageCategory || null
    }

    if (conv.messages.length === 0) {
      conv.title = generateConversationTitle(text || 'Image Analysis')
    }

    addMessage(conv.id, userMessage)
    
    const inputText = text
    const inputImages = [...attachedFiles]
    const inputCategory = imageCategory
    
    setText('')
    setAttachedFiles([])
    setImageCategory('')
    setIsTyping(true)

    // Build context including the user message we just added
    const recent = [...conv.messages, userMessage].slice(-6).map(m => ({ type: m.type, text: m.text }))
    
    const reply = await callBackendAPI(
      inputImages.map(img => ({ url: img.url, name: img.name })),
      inputText,
      recent,
      inputCategory
    )

    setIsTyping(false)

    const botMessage = {
      text: reply,
      type: 'bot',
      timestamp: Date.now()
    }

    // Save conversation after bot message is added
    addMessage(conv.id, botMessage, (updatedConv) => {
      saveConversation(updatedConv)
    })
  }

  return (
    <div id="app-wrapper">
      <header className="top-bar">
        <div className="brand">
          <img src="/agrochat-logo.jpg" alt="AgroChat" className="brand-logo" />
          <span className="brand-name">AgroChat</span>
        </div>
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <button className="new-chat-button" onClick={startNewConversation}>
            <span className="new-chat-icon">+</span> New Chat
          </button>
          <div className="conversation-list-container">
            {conversations.length === 0 ? (
              <div className="empty-conversations">No conversations yet</div>
            ) : (
              conversations.map(c => (
                <div
                  key={c.id}
                  className={`conversation ${c.id === currentConversationId ? 'active' : ''}`}
                  onClick={() => setCurrentConversationId(c.id)}
                >
                  <span className="conversation-title">{c.title}</span>
                  <button
                    className="conversation-delete"
                    onClick={(e) => deleteConversation(c.id, e)}
                    disabled={deletingConvId === c.id}
                    title="Delete conversation"
                  >
                    {deletingConvId === c.id ? '...' : '×'}
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        <main className="chat-panel">
          <div className="chat-messages" ref={messagesRef}>
            {(!currentConv || currentConv.messages.length === 0) ? (
              <div className="welcome-message">
                <h2>Welcome to AgroChat</h2>
                <p>Ask me anything about agriculture, plant diseases, or weather!</p>
              </div>
            ) : (
              currentConv.messages.map((m, i) => (
                <div key={i} className={`msg ${m.type}`}>
                  {m.images && m.images.length > 0 && (
                    <div className="msg-images">
                      {m.images.map((img, idx) => (
                        <div key={idx} className="msg-image-container">
                          <img
                            src={img.url}
                            alt={img.name}
                            className="msg-image"
                            onClick={() => setExpandedImage(img.url)}
                          />
                          {m.category && (
                            <span className="image-category-badge">{m.category}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="msg-text" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                </div>
              ))
            )}
            {isTyping && (
              <div className="msg bot typing-indicator">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            )}
          </div>

          {/* Suggestion buttons - always visible */}
          <div className="quick-actions">
            <button onClick={() => handleSuggestion('weather')} title="Get weather information">
              🌤️ Check Today's Weather
            </button>
            <button onClick={() => handleSuggestion('disease')} title="Identify plant disease">
              🍃 Plant Disease
            </button>
            <button onClick={() => handleSuggestion('insect')} title="Identify insect">
              🐛 Insect Identification
            </button>
          </div>

          {/* Category selector - show when images are attached */}
          {attachedFiles.length > 0 && (
            <div className="image-category-selector">
              <span className="category-label">Category:</span>
              <select
                className="category-select"
                value={imageCategory}
                onChange={(e) => setImageCategory(e.target.value)}
              >
                <option value="">Select category...</option>
                <option value="disease">Disease</option>
                <option value="insect">Insect</option>
              </select>
            </div>
          )}

          {/* Image preview */}
          {attachedFiles.length > 0 && (
            <div className="attached-files">
              {attachedFiles.map((file, idx) => (
                <div key={idx} className="attached-file-item">
                  <img src={file.url} alt={file.name} className="file-preview" />
                  <span className="file-name">{file.name}</span>
                  <button
                    className="file-remove"
                    onClick={() => removeFile(idx)}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <button
              type="button"
              className="attach-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Attach image"
            >
              📎
            </button>
            <input
              type="text"
              value={text}
              onChange={(e) => {
                setText(e.target.value)
                // Reset placeholder when user starts typing
                if (e.target.value && e.target.placeholder !== "Type your message...") {
                  e.target.placeholder = "Type your message..."
                }
              }}
              placeholder="Type your message..."
              className="chat-input-field"
            />
            <button type="submit" className="send-btn" disabled={!text.trim() && attachedFiles.length === 0}>
              ➤
            </button>
          </form>
        </main>
      </div>

      {/* Image modal */}
      {expandedImage && (
        <div className="image-modal" onClick={() => setExpandedImage(null)}>
          <div className="image-modal-content">
            <button
              className="image-modal-close"
              onClick={() => setExpandedImage(null)}
            >
              ×
            </button>
            <img src={expandedImage} alt="Expanded" className="image-modal-image" />
          </div>
        </div>
      )}
    </div>
  )
}
