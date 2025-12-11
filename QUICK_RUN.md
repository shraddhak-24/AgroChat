# ⚡ Quick Terminal Commands (Copy & Paste)

## Terminal 1: Install & Start Backend

```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend"
pip install -r requirements.txt
.\run.ps1
```

⏳ **Wait for**: `Uvicorn running on http://127.0.0.1:8000`

---

## Terminal 2: Start Frontend

```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\frontend"
npm install
npm run dev
```

⏳ **Wait for**: `Local: http://127.0.0.1:5173`

---

## Browser: Open App

```
http://127.0.0.1:5173
```

---

## Terminal 3: Quick API Tests (Optional)

### Test 1: Health Check
```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -Method Get | ConvertFrom-Json | Format-Table
```

**Expected**: `status = healthy`

### Test 2: List Diseases
```powershell
Invoke-WebRequest http://127.0.0.1:8000/diseases -Method Get | ConvertFrom-Json | Format-List
```

**Expected**: Shows 15 classes

### Test 3: API Documentation
```
http://127.0.0.1:8000/docs
```

**Expected**: Swagger UI opens with all endpoints

---

## That's It! 🎉

Just run those 3 terminal commands in order:
1. Terminal 1: Backend
2. Terminal 2: Frontend  
3. Browser: http://127.0.0.1:5173

Then upload an image and test!

---

## 🆘 If Something Fails

### Backend won't start
```powershell
# Kill process on port 8000
netstat -ano | findstr :8000
Stop-Process -Id <PID> -Force

# Try again
python app.py
```

### Missing torch
```powershell
pip install --upgrade torch torchvision
```

### Missing checkpoint
```powershell
Copy-Item "C:\Users\sreeh\Downloads\efficientnet_b0_best.pth" `
  "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\models\"
```

### Frontend npm errors
```powershell
cd frontend
rm -r node_modules
npm install
npm run dev
```

---

**See `TEST_STEPS.md` for detailed testing guide**
