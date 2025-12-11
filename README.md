AgroChat — Workspace Layout

This project scaffold keeps `frontend` intact and provides folders for backend, models, data and notebooks.

Top-level layout (created):
- frontend/           # your existing frontend app (do not modify if you requested preservation)
- backend/            # FastAPI server, RAG glue, LLaMA wrapper, weather integration
- models/             # local LLaMA ggml file(s), CNN checkpoints
- data/               # datasets, vectorstore files (FAISS), CSVs
- notebooks/          # place `cnnaccuracy.ipynb`, `llm.ipynb`, and others here

What I added
- directories: `backend/`, `backend/services/`, `models/`, `data/`, `notebooks/`
- helpful files: `backend/requirements.txt`, `notebooks/README.md`, `MODEL_README.md`, and `RUN_CHECKS.md` (see below)

Next steps
1. Copy your notebooks `cnnaccuracy.ipynb` and `llm.ipynb` into `notebooks/`.
2. Place LLaMA ggml model into `models/` and set `LLAMA_MODEL_PATH` before starting backend.
3. Paste backend scripts into `backend/` and `backend/services/`.

If you want, I can try to search other folders on your machine for the notebooks and move them here — tell me if you want me to search `Downloads` or other locations.
