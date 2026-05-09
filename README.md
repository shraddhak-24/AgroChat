# 🌱 AgroChat - Plant Disease Detection & Agricultural Assistant

A comprehensive agricultural chatbot that uses AI to detect plant diseases, provide treatment advice, and answer farming questions. AgroChat combines computer vision and conversational AI to support farmers with real-time agricultural assistance.


## 📁 Project Structure

```
AgroChat/
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── pages/        # Chat, Login, Admin pages
│   │   └── styles.css    # Styling
│   └── package.json
│
├── backend/               # FastAPI backend server
│   ├── app.py            # Main API server
│   ├── db.py             # Database operations
│   ├── services/         # RAG and vision services
│   ├── models/           # CNN model checkpoint
│   └── data/             # SQLite database
│
└── notebooks/             # Jupyter notebooks for training
```

## 🚀 Quick Start

### 1. Start Backend
```powershell
cd backend
pip install -r requirements.txt
python app.py
```
Wait for: `Uvicorn running on http://127.0.0.1:8000`

### 2. Start Frontend
```powershell
cd frontend
npm install
npm run dev
```
Wait for: `Local: http://127.0.0.1:5173`

### 3. Open Browser
Visit: **http://127.0.0.1:5173**

## ✨ Features

- 🔍 **Plant Disease Detection**: Upload images to identify plant diseases
- 💬 **Smart Chatbot**: Ask questions about agriculture and farming
- 🌤️ **Weather Integration**: Get weather information for your location
- 📝 **Conversation History**: Save and manage your conversations
- 🎯 **Quick Actions**: One-click buttons for common queries
- 🖼️ **Image Analysis**: Upload multiple images with category selection

## 🛠️ Configuration

### Weather API (Optional)
Create a `.env` file in `backend/`:
```
WEATHER_KEY=your_openweathermap_api_key
```
Get your API key from: https://openweathermap.org/api

### Model Checkpoint
Place `efficientnet_b0_best.pth` in `backend/models/`

## 📚 API Documentation

Once backend is running, visit: **http://127.0.0.1:8000/docs**

## 🐛 Troubleshooting

See `ERROR_TROUBLESHOOTING.md` for common issues and solutions.

## 📖 Documentation

All documentation has been organized in the `docs/` folder:
- **Quick Start**: `docs/QUICKSTART.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Error Help**: `docs/ERROR_TROUBLESHOOTING.md`
- **Backend API**: `backend/README.md`
- **Full Documentation**: `docs/README.md`

---

**Built with**: React, FastAPI, PyTorch, EfficientNet 
