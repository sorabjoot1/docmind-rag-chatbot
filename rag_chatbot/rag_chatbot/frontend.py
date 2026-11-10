"""
frontend.py - The web interface: serves the chat page and a small JSON API.
"""
import logging

from flask import Flask, jsonify, render_template, request

import config
from llm_client import LLMError, is_configured
from prompts import DEFAULT_PATTERN, PATTERN_INFO, PATTERNS
from rag_pipeline import PipelineNotReady

logger = logging.getLogger(__name__)

SUGGESTIONS = [
    {"icon": "book", "text": "What is the punishment for theft?"},
    {"icon": "bulb", "text": "How does the code define 'dishonestly'?"},
    {"icon": "list", "text": "What is criminal conspiracy?"},
    {"icon": "child", "text": "Explain Section 34 (common intention) in simple words."},
]


def create_app(pipeline):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.get("/")
    def index():
        return render_template("index.html", app_name=config.APP_NAME)

    @app.get("/api/config")
    def api_config():
        return jsonify(
            app_name=config.APP_NAME,
            default_pattern=DEFAULT_PATTERN,
            patterns=[{"name": n, "description": PATTERN_INFO.get(n, "")} for n in PATTERNS],
            suggestions=SUGGESTIONS,
            max_question_chars=config.MAX_QUESTION_CHARS,
        )

    @app.get("/api/status")
    def api_status():
        return jsonify(**pipeline.status(), api_key_set=is_configured())

    @app.post("/api/init")
    def api_init():
        pipeline.start()
        return jsonify(**pipeline.status(), api_key_set=is_configured())

    @app.post("/api/chat")
    def api_chat():
        data = request.get_json(silent=True) or {}
        question = str(data.get("question", "")).strip()
        if not question:
            return jsonify(error="Please type a question first."), 400
        if len(question) > config.MAX_QUESTION_CHARS:
            return jsonify(error=f"Question is too long (max {config.MAX_QUESTION_CHARS} characters)."), 400

        pattern = data.get("pattern", DEFAULT_PATTERN)
        history = data.get("history", [])
        if not isinstance(history, list):
            history = []

        try:
            return jsonify(pipeline.ask(question, pattern, history))
        except PipelineNotReady as e:
            return jsonify(error=str(e)), 503
        except LLMError as e:
            return jsonify(error=str(e)), 502
        except Exception as e:
            logger.error("Chat request failed: %s", type(e).__name__)
            return jsonify(error="Something went wrong while answering. Please try again."), 500

    return app
