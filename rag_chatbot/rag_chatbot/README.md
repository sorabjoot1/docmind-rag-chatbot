# DocMind - RAG Chatbot

A document question-answering chatbot built on your existing RAG pipeline
(6 chunking techniques, `all-mpnet-base-v2` embeddings, ChromaDB, Hybrid Search,
7 prompt patterns, OpenRouter LLM) with a modern web interface.

The document in `data/` is **pakistan_penal_code.txt**. You can replace it with any `.pdf` or `.txt` file.

## Project structure

```
rag_chatbot/
├── main.py              # Entry point - run this
├── config.py            # All settings
├── document_loader.py   # Finds and loads the PDF / TXT
├── chunking.py          # The 6 chunking techniques
├── embeddings.py        # Embedding model (loaded once)
├── vector_store.py      # ChromaDB storage (saved on disk)
├── hybrid_search.py     # Hybrid Search (semantic + keyword)
├── prompts.py           # Root prompt + 7 prompt patterns
├── llm_client.py        # OpenRouter LLM connection
├── rag_pipeline.py      # Connects everything into the RAG workflow
├── frontend.py          # Web interface (Flask routes)
├── templates/index.html
├── static/style.css
├── static/app.js
├── data/                # Your document goes here
├── requirements.txt
├── .env.example         # Copy to .env and add your key
└── .gitignore
```

## Run in VS Code

1. Install **Python 3.10 or newer**, then open the `rag_chatbot` folder in VS Code (File -> Open Folder).
2. Open the terminal (Terminal -> New Terminal) and create a virtual environment:

   Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   macOS / Linux:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Add your API key. Copy `.env.example` to a new file named `.env` and write your OpenRouter key:
   ```
   OPENROUTER_API_KEY=your-new-key-here
   ```
   Get a key at https://openrouter.ai/keys
5. Start the app:
   ```
   python main.py
   ```
   Your browser opens at http://127.0.0.1:5000 . Stop the app with `Ctrl+C`.

## First start vs. next starts

* **First start:** the embedding model downloads (about 400 MB) and the document is chunked and indexed.
  For a large document like the Penal Code this can take several minutes on a normal CPU. The page opens immediately and shows a progress banner.
* **Next starts:** the saved ChromaDB in `storage/` is reused - ready in seconds.
  If you change the document, it is re-indexed automatically.

## Using a different document

Delete the old file from `data/`, copy your `.pdf` or `.txt` in, and restart the app.

## Troubleshooting

| Problem | Fix |
|---|---|
| "OpenRouter API key is missing" | Create the `.env` file (step 4) and restart |
| "OpenRouter rejected the API key" | The key is wrong or revoked - create a new one |
| "No document found" | Put a `.pdf` or `.txt` file inside `data/` |
| Banner stays on "Preparing..." for long | Normal on the first start for big documents - check the terminal for progress |
| Port already in use | Add `PORT=5001` to `.env` |
