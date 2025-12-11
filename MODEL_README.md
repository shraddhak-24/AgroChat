Models folder — what to put in `models/`

Place the following files in this folder:

- Local LLaMA ggml model:
  - Example file name: `ggml-llama-3.1b.bin` or similar.
  - Set environment variable before starting backend:
    - PowerShell: `$env:LLAMA_MODEL_PATH = 'C:\path\to\models\ggml-llama-3.1b.bin'`
    - Linux/macOS: `export LLAMA_MODEL_PATH=/path/to/ggml-llama-3.1b.bin`

- CNN checkpoints (optional):
  - `plant_cnn.pth`
  - `pest_cnn.pth`

- FAISS index files (optional):
  - `faiss_index.bin` (or similar), plus a JSON/CSV for metadata

Notes
- LLaMA ggml model files are large (multi-GB). Make sure you have enough disk space and the correct model format for `llama-cpp-python`.
- Building ggml from official checkpoints may require conversion tools; I can add a script if you need it.
