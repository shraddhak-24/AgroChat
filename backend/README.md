# AgroChat Backend API Documentation

## Overview

The AgroChat backend is a FastAPI application that integrates:
- **CNN Vision Model** (EfficientNet-B0) for plant disease detection
- **RAG System** for knowledge-based retrieval
- **LLM Integration** (Ollama, llama-cpp-python, or stub mode)
- **CORS-enabled** for React frontend communication

## Setup

### Prerequisites
- Python 3.9+
- pip or conda
- Checkpoint file: `efficientnet_b0_best.pth` (auto-detected in `models/` folder)

### Installation

1. **Navigate to backend folder**:
   ```powershell
   cd c:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Place checkpoint file** (if not already there):
   - Copy `efficientnet_b0_best.pth` to `../models/` folder
   - Backend will auto-detect it on startup

4. **(Optional) Install Ollama for real LLM**:
   - Download from [ollama.ai](https://ollama.ai)
   - Run: `ollama pull llama3.2:1b`
   - Keep Ollama running in background while using backend

### Running the Backend

**Option 1: PowerShell Script (Easy)**
```powershell
.\run.ps1
```

**Option 2: Direct Python**
```powershell
python app.py
```

**Option 3: Uvicorn with Custom Settings**
```powershell
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

## API Endpoints

### 1. Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "llm_mode": "ollama",
  "device": "cpu",
  "cnn_classes": 15
}
```

### 2. Analyze Single Image (Main Endpoint)
```
POST /analyze
```
**Parameters:**
- `image` (file, required): Plant leaf/fruit image
- `question` (string, optional): User's question about disease/treatment
  - Default: "What treatment do you recommend?"

**Example Request** (using curl):
```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "image=@leaf.jpg" \
  -F "question=How can I treat this organically?"
```

**Response:**
```json
{
  "success": true,
  "disease": "Tomato Early Blight",
  "confidence": 92.5,
  "advice": "Symptoms: Brown leaf rings...\nOrganic Control: Neem oil...",
  "llm_mode": "ollama"
}
```

### 3. Analyze Multiple Images
```
POST /analyze_batch
```
**Parameters:**
- `images` (list[file], required): Multiple plant images
- `question` (string, optional): Question for all images

**Response:**
```json
{
  "results": [
    {
      "image": "leaf1.jpg",
      "disease": "Tomato Early Blight",
      "confidence": 92.5,
      "advice": "..."
    },
    {
      "image": "leaf2.jpg",
      "disease": "Potato Late Blight",
      "confidence": 88.3,
      "advice": "..."
    }
  ]
}
```

### 4. Get Disease Information
```
GET /disease/{disease_name}
```
**Example:**
```
GET /disease/Tomato_Early_blight
```

**Response:**
```json
{
  "disease": "Tomato_Early_blight",
  "knowledge": "Tomato Early Blight:\n- Symptoms: Brown leaf rings...\n- Cause: Alternaria solani..."
}
```

### 5. List All Diseases
```
GET /diseases
```

**Response:**
```json
{
  "total": 15,
  "classes": [
    "Pepper__bell___Bacterial_spot",
    "Pepper__bell___healthy",
    "Potato___Early_blight",
    ...
  ],
  "class_to_title_mapping": {
    "Pepper__bell___Bacterial_spot": "Pepper Bell Bacterial Spot",
    ...
  }
}
```

## Interactive API Documentation

Once backend is running, visit:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

You can test all endpoints directly from the browser!

## LLM Modes

### Mode 1: Ollama (Recommended)
- **Auto-detected** if Ollama is installed and running
- **Model**: llama3.2:1b
- **Setup**: 
  ```powershell
  # Install Ollama from ollama.ai, then:
  ollama pull llama3.2:1b
  # Keep running while using backend
  ```

### Mode 2: llama-cpp-python
- **Auto-detected** if `llama-cpp-python` package is installed
- **Setup**:
  ```powershell
  pip install llama-cpp-python
  # Set environment variable
  $env:LLAMA_MODEL_PATH = "C:\path\to\model.ggml"
  ```

### Mode 3: Stub (Testing)
- **Fallback** if no LLM is available
- **Useful** for testing UI/API without LLM installed
- **Response**: Generic placeholder answers

## Frontend Integration

The React frontend calls the backend at:
```javascript
const API_BASE = "http://127.0.0.1:8000";

// Example: Upload and analyze image
const formData = new FormData();
formData.append("image", imageFile);
formData.append("question", userQuestion);

const response = await fetch(`${API_BASE}/analyze`, {
  method: "POST",
  body: formData,
});
```

## Troubleshooting

### Issue: "Checkpoint file not found"
**Solution**: Ensure `efficientnet_b0_best.pth` is in one of these locations:
- `backend/models/efficientnet_b0_best.pth`
- `models/efficientnet_b0_best.pth` (relative to `backend/`)
- `checkpoints/efficientnet_b0_best.pth`
- Downloads folder
- AgroChat workspace root

### Issue: "No module named 'torch'"
**Solution**:
```powershell
pip install --upgrade torch torchvision
```

### Issue: "Ollama connection failed"
**Solution**:
- Ensure Ollama is installed and running
- Check: `ollama --version`
- If not installed: Download from [ollama.ai](https://ollama.ai)

### Issue: CORS errors from frontend
**Solution**: Backend already has CORS enabled. If still issues:
- Check that frontend URL matches `allow_origins` in `app.py`
- Currently allows all origins (`allow_origins=["*"]`)

## Development Notes

### Model Architecture
- **CNN**: EfficientNet-B0 (trained on PlantVillage dataset)
- **Classes**: 15 plant disease + health categories
- **Input**: 224x224 RGB image
- **Output**: Disease class + confidence score

### RAG System
- **Type**: Deterministic keyword-matching (not semantic search)
- **Knowledge Base**: Hardcoded plant disease information
- **Retrieval**: Maps CNN class name → disease description
- **No external DB needed**: All knowledge embedded in code

### LLM Integration
- **Function**: `ask_offline_llm(prompt)` 
- **Behavior**: Strict information extraction from RAG
- **Purpose**: Format and explain RAG-retrieved knowledge
- **Fallback**: Stub mode if no LLM available

## Performance Tips

1. **Use GPU** if available:
   - Install CUDA-enabled PyTorch for 10x speedup
   - Check: Model will auto-detect CUDA in `DEVICE` variable

2. **Batch Processing**:
   - Use `/analyze_batch` for multiple images
   - Reduces per-image overhead

3. **Model Optimization**:
   - Consider quantization (convert to ONNX) for production
   - Current: Full-precision float32 (accurate but larger)

## Future Enhancements

- [ ] Add pest/insect detection model (second CNN)
- [ ] Integrate weather API for localized recommendations
- [ ] Add semantic RAG with embeddings (FAISS)
- [ ] User authentication & image history
- [ ] Database storage (PostgreSQL/MongoDB)
- [ ] Model versioning & A/B testing

## Support

For issues or questions, check:
1. Backend logs (console output)
2. Frontend network tab (HTTP requests)
3. API docs: http://127.0.0.1:8000/docs

---

**Version**: 1.0.0  
**Last Updated**: December 2025
