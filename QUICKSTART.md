# Quick Start (5 Minutes)

## 1️⃣ Install Dependencies (2 min)

```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend"
pip install -r requirements.txt
```

## 2️⃣ Start Backend (Terminal 1)

```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend"
.\run.ps1
```

✅ **Wait for message**: `Uvicorn running on http://127.0.0.1:8000`

## 3️⃣ Start Frontend (Terminal 2)

```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\frontend"
npm install  # Only if first time
npm run dev
```

✅ **Wait for message**: `Local: http://127.0.0.1:5173`

## 4️⃣ Open Browser

Visit: **http://127.0.0.1:5173**

## 5️⃣ Test (Upload Plant Image)

1. Login with credentials
2. Go to "Chat" page
3. Upload a plant leaf image
4. Ask a question
5. See disease detection + advice

## 🧪 API Testing (Optional)

Visit: **http://127.0.0.1:8000/docs**
- Try `/analyze` endpoint
- Upload image
- Click "Execute"

## ❌ If Something Fails

### Backend won't start
```powershell
# Check Python
python --version

# Reinstall dependencies
pip install --upgrade torch torchvision fastapi uvicorn

# Check checkpoint file exists
Test-Path "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\models\efficientnet_b0_best.pth"
```

### Frontend won't start
```powershell
# Reinstall node modules
rm -r node_modules package-lock.json
npm install
npm run dev
```

### API returns errors
```powershell
# Check API health
Invoke-WebRequest http://127.0.0.1:8000/health -Method Get | ConvertFrom-Json
```

## 📖 Full Docs

- **Backend API**: `backend/README.md`
- **Integration**: `INTEGRATION_GUIDE.md`
- **Changes**: `CHANGES_SUMMARY.md`

---

**That's it! System is now running.** 🚀
