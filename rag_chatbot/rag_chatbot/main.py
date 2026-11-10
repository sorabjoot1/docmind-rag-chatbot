"""
main.py - Application entry point.   Run with:  python main.py

1. Starts preparing the RAG pipeline in the background (PDF -> chunks -> vector DB).
2. Immediately shows the frontend, so the page opens without waiting.
"""
import logging
import threading
import warnings
import webbrowser

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Relevance scores must be between")

import config
from frontend import create_app
from llm_client import is_configured
from rag_pipeline import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("werkzeug").setLevel(logging.WARNING)

app = create_app(pipeline)


def main():
    if not is_configured():
        print("WARNING: OPENROUTER_API_KEY is not set. Create a .env file (see .env.example).")

    pipeline.start()  # background thread: the page opens right away

    url = f"http://{config.HOST}:{config.PORT}"
    print(f"\n{config.APP_NAME} is running at {url}  (press Ctrl+C to stop)\n")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
