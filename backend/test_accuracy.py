"""
Simple accuracy test script for AgroChat backend `/analyze` endpoint.

Usage:
  - Place labeled test images under `backend/test_images/`.
  - Create a JSON file `backend/test_images/labels.json` mapping filenames to expected class names, e.g.
    {
      "leaf1.jpg": "Potato___Late_blight",
      "leaf2.jpg": "Tomato_Early_blight"
    }
  - Run from backend folder (inside the venv):
      python test_accuracy.py

This script will POST each image to the running backend and record predictions.
It does NOT change any model weights and only issues HTTP requests.
"""

import os
import json
import time
import requests
from pathlib import Path

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://127.0.0.1:8005')
IMAGES_DIR = Path(__file__).parent / 'test_images'
LABELS_FILE = IMAGES_DIR / 'labels.json'

assert IMAGES_DIR.exists(), f"Create a test images folder at {IMAGES_DIR} and add images and a labels.json"
assert LABELS_FILE.exists(), f"Create labels.json mapping filenames to expected classes at {LABELS_FILE}"

with open(LABELS_FILE, 'r', encoding='utf-8') as f:
    labels = json.load(f)

results = []
start = time.time()
for fname, expected in labels.items():
    img_path = IMAGES_DIR / fname
    if not img_path.exists():
        print(f"Skipping {fname}: file not found")
        continue

    files = {'image': open(img_path, 'rb')}
    params = {'question': 'Test: what is the predicted disease?'}
    try:
        r = requests.post(f"{BACKEND_URL}/analyze", params=params, files=files, timeout=30)
    except Exception as e:
        print(f"Error calling backend for {fname}: {e}")
        results.append((fname, expected, None, False, str(e)))
        continue

    if r.status_code != 200:
        print(f"Backend returned {r.status_code} for {fname}: {r.text}")
        results.append((fname, expected, None, False, f"status {r.status_code}"))
        continue

    data = r.json()
    pred = data.get('disease')
    ok = (pred == expected)
    results.append((fname, expected, pred, ok, data.get('advice')))
    print(f"{fname}: expected={expected} predicted={pred} ok={ok}")

end = time.time()
acc = sum(1 for r in results if r[3]) / max(1, len(results))
print('\n--- Summary ---')
print(f'Tested {len(results)} images in {end-start:.1f}s')
print(f'Accuracy: {acc*100:.2f}%')

# Save report
report_file = Path(__file__).parent / 'test_report.json'
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump({'results': results, 'accuracy': acc, 'tested': len(results)}, f, ensure_ascii=False, indent=2)

print(f'Report written to {report_file}')
