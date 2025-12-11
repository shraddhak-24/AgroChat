Notebook & Code Checklist — how to verify each notebook contains necessary components

Place your notebooks (e.g. `cnnaccuracy.ipynb`, `llm.ipynb`) into `notebooks/` and verify the following sections exist in each:

1) CNN / Vision (cnnaccuracy.ipynb)
- Data loading: code that reads images from `data/` or a dataset path.
- Preprocessing: resize, normalize, augment functions.
- Model architecture: PyTorch or TensorFlow CNN model definition for plant detection.
- Training loop or inference code: optimizer, loss, epochs (if training), or a `model.eval()` inference cell.
- Accuracy metrics: printing or plotting accuracy/loss curves and confusion matrix.
- Saving/loading checkpoints: `torch.save()` and `torch.load()` or TF equivalents.

2) RAG / Vector store
- Text splitter and chunking (e.g. `langchain_text_splitters` or custom splitter).
- Embeddings: usage of `sentence-transformers` or another embedding model.
- FAISS or Chroma indexing: code that builds an index and persists it to `data/`.
- Retriever and top-k search calls.

3) LLM integration (llm.ipynb)
- If using local LLaMA: import `llama_cpp` or other local runtime.
- Check for environment variable usage: `LLAMA_MODEL_PATH`.
- Prompt construction and generation code.
- If previously using a cloud API (Groq, OpenAI), look for that code to replace with local LLaMA calls.

4) Weather API
- Look for `requests` to external weather API, or usage of a provider SDK.
- Ensure there is code to request weather by location (lat/lon) and parse temperature/humidity/rain/wind.
- Store or return weather context to be combined with CNN and RAG features.

5) Glue code / orchestration
- A function that accepts user input (image + optional text), calls preprocessing, CNNs, weather API, runs retrieval, then calls the LLM to generate an answer.
- Check for saving results to `data/` or DB and returning structured output.

6) Dependencies & environment
- Each notebook should list required pip packages in a cell or attach a `requirements.txt` listing packages like `torch`, `torchvision`, `sentence-transformers`, `faiss-cpu`, `llama-cpp-python`, `fastapi`, `uvicorn`, `requests`, etc.

If any item above is missing in your notebooks, note it here and I will help you add the missing code/boilerplate.
