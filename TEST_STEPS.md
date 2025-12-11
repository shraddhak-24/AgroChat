# 🧪 Complete App Testing Guide

## Prerequisites Check

Before starting, verify these are installed:

```powershell
# Check Python
python --version
# Expected: Python 3.9+

# Check Node.js
node --version
npm --version
# Expected: Node 16+

# Check pip
pip --version
```

---

## Step 1: Install Backend Dependencies (5 minutes)

```powershell
# Navigate to backend
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend"

# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list | grep -E "torch|fastapi|uvicorn|efficientnet"
```

**Expected output**: Shows installed packages  
**If errors**: Run `pip install --upgrade pip` first

---

## Step 2: Verify Checkpoint File

```powershell
# Check if model file exists
Test-Path "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\models\efficientnet_b0_best.pth"

# Expected: True
```

**If FALSE**: 
```powershell
# Check Downloads
Test-Path "C:\Users\sreeh\Downloads\efficientnet_b0_best.pth"

# Copy if found
Copy-Item "C:\Users\sreeh\Downloads\efficientnet_b0_best.pth" `
  "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\models\"
```

---

## Step 3: Start Backend (Terminal 1)

```powershell
# Terminal 1
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend"

# Option A: Use startup script
.\run.ps1

# Option B: Direct Python (if script fails)
python app.py
```

**Wait for this message**:
```
============================================================
🚀 AgroChat Backend Starting...
============================================================
📍 API: http://127.0.0.1:8000
📚 Docs: http://127.0.0.1:8000/docs
🤖 LLM: OLLAMA (or STUB)
============================================================

INFO:     Started server process [xxxx]
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**If stuck on "Loading model"**: Wait 30+ seconds (first-time model load)

---

## Step 4: Test Backend Health (Terminal 2)

**Open a new terminal while backend runs**:

```powershell
# Test health endpoint
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -Method Get
$response.Content | ConvertFrom-Json | Format-Table
```

**Expected output**:
```
status      llm_mode device cnn_classes
------      -------- ------ -----------
healthy     ollama   cpu            15
```

✅ **Backend is working!**

---

## Step 5: Install Frontend Dependencies (Terminal 2)

```powershell
# Navigate to frontend
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\frontend"

# Check if node_modules exists
if (-Not (Test-Path "node_modules")) {
    npm install
    Write-Host "✅ Dependencies installed"
} else {
    Write-Host "✅ Dependencies already installed"
}
```

**Expected**: `added XXX packages` (or already installed message)

---

## Step 6: Start Frontend (Terminal 2)

```powershell
# Same terminal, still in frontend folder
npm run dev
```

**Wait for this message**:
```
  ➜  Local:   http://127.0.0.1:5173/
  ➜  press h to show help
```

---

## Step 7: Open App in Browser

```powershell
# Open browser (or paste into address bar)
http://127.0.0.1:5173
```

**You should see**: Login page with credential fields

---

## Step 8: Login Test

**On Login page**:
1. Enter username: (use any text)
2. Enter password: (use any text)
3. Click "Login"

**Expected**: Should proceed to Admin page

---

## Step 9: Test Admin Page

**On Admin page**:
1. You should see admin settings/dashboard
2. Try clicking around to verify UI loads

**Expected**: No console errors, page is interactive

---

## Step 10: Test Chat Page

**On Chat page**:
1. You should see image upload area
2. Text field for questions

**For now**: Don't upload yet

---

## Step 11: Test API Directly (Terminal 3)

**Open a new terminal**:

```powershell
# Test /diseases endpoint
Invoke-WebRequest -Uri "http://127.0.0.1:8000/diseases" -Method Get | 
  ConvertFrom-Json | Format-Table
```

**Expected output**:
```
total classes                              class_to_title_mapping
----- -------                              ----------------------
   15 {Pepper__bell___Bacterial_spot...}   @{Pepper__bell___Bacterial_spot=Pepper Bell Bacterial Spot...}
```

✅ **API is working!**

---

## Step 12: Test Image Upload (Browser)

**On Chat page**:

1. **Prepare test image**:
   - Use any plant leaf image from Downloads
   - Or create dummy image (~100KB)

2. **Upload image**:
   - Click "Choose File"
   - Select image
   - Leave question as default: "What treatment do you recommend?"
   - Click "Analyze" button

3. **Expected response**:
   ```
   Disease: Tomato Early Blight
   Confidence: 92.5%
   Advice: [Disease information from knowledge base]
   ```

---

## Step 13: Test with curl (Terminal 3)

**For more control, test API directly**:

```powershell
# Find an image file
$imagePath = "C:\path\to\plant\image.jpg"  # Change to actual path

# Send to backend
$response = Curl -X POST `
  -F "image=@$imagePath" `
  -F "question=How to treat this organically?" `
  http://127.0.0.1:8000/analyze

# View response
$response | ConvertFrom-Json | Format-List
```

**Expected**:
```
success : True
disease : Tomato Early Blight
confidence : 92.5
advice : Symptoms: Brown leaf rings...
llm_mode : ollama
```

---

## Step 14: Test Interactive API Docs

```
Visit: http://127.0.0.1:8000/docs
```

**You should see**:
- Swagger UI with all 5 endpoints
- Green "Try it out" buttons on each endpoint

**Test `/analyze` endpoint**:
1. Click on `/analyze` (POST)
2. Click "Try it out"
3. Upload an image file
4. Click "Execute"
5. See response below

---

## Full System Test Checklist

- [ ] Backend starts without errors
- [ ] Health check returns healthy status
- [ ] Frontend loads at http://127.0.0.1:5173
- [ ] Login page appears
- [ ] Can login and reach Chat page
- [ ] Can upload image in Chat page
- [ ] Image analysis returns disease + confidence
- [ ] LLM advice appears (or STUB message if no Ollama)
- [ ] API docs work at /docs
- [ ] No console errors in browser (F12)
- [ ] No errors in backend terminal

---

## Troubleshooting

### Problem: Backend won't start

```powershell
# Check if port 8000 is already in use
netstat -ano | findstr :8000

# Kill process using port 8000
$process = Get-Process -ID (Get-NetTCPConnection -LocalPort 8000).OwningProcess
$process | Stop-Process -Force

# Try starting backend again
python app.py
```

### Problem: "Module not found: torch"

```powershell
cd backend
pip install --upgrade torch torchvision
```

### Problem: "Checkpoint not found"

```powershell
# Verify checkpoint exists
Test-Path "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\models\efficientnet_b0_best.pth"

# If false, copy from Downloads
Copy-Item "C:\Users\sreeh\Downloads\efficientnet_b0_best.pth" `
  "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\models\"
```

### Problem: Frontend won't start (npm errors)

```powershell
cd frontend
rm -r node_modules package-lock.json
npm install
npm run dev
```

### Problem: "CORS error" in browser

✅ Already configured. If still happening:
- Clear browser cache (Ctrl+Shift+Delete)
- Close and reopen browser
- Check console (F12) for actual error

### Problem: Image upload hangs

- Check backend terminal for errors
- Try uploading smaller image (<5MB)
- Check if Ollama is running (if using LLM mode)

---

## Expected Timeline

| Step | Time | Status |
|------|------|--------|
| Install dependencies | 5 min | ⏳ |
| Start backend | 30s | ⏳ |
| Start frontend | 30s | ⏳ |
| Test in browser | 5 min | ⏳ |
| Full system test | 10 min | ⏳ |
| **Total** | **21 min** | ⏳ |

---

## Success Indicators

✅ **You know it's working when**:

1. Backend shows: `Uvicorn running on http://127.0.0.1:8000`
2. Frontend shows: `Local: http://127.0.0.1:5173`
3. Browser shows app UI at localhost:5173
4. Image upload returns disease name + confidence
5. LLM advice displays (or STUB message)
6. No red errors in browser console (F12)
7. No red errors in backend terminal

---

## Next Steps After Success

### If all tests pass ✅:
1. Try with different plant images
2. Test different questions in Chat
3. Monitor backend terminal for errors
4. Check browser console (F12) for warnings

### If errors occur ❌:
1. Note the exact error message
2. Check the Troubleshooting section above
3. Review backend logs in terminal
4. Check browser console (F12) for frontend errors

---

## Command Reference (Quick Copy-Paste)

**Terminal 1 (Backend)**:
```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\backend"
pip install -r requirements.txt
.\run.ps1
```

**Terminal 2 (Frontend)**:
```powershell
cd "C:\Users\sreeh\OneDrive\Documents\Desktop\AgroChat\frontend"
npm install
npm run dev
```

**Terminal 3 (Testing)**:
```powershell
# Test health
Invoke-WebRequest http://127.0.0.1:8000/health -Method Get | ConvertFrom-Json | Format-Table

# Test diseases list
Invoke-WebRequest http://127.0.0.1:8000/diseases -Method Get | ConvertFrom-Json | Format-List
```

**Browser**:
```
Frontend: http://127.0.0.1:5173
API Docs: http://127.0.0.1:8000/docs
```

---

**Start with Terminal 1 (Backend) → Terminal 2 (Frontend) → Browser**

Good luck! 🚀
