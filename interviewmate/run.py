#!/usr/bin/env python3
"""
run.py – Entry point for InterviewMate AI
Usage: python run.py
"""

import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

from app import app, db

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("[OK] Database initialized")

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "true").lower() == "true"

    print(f"\nInterviewMate AI running at http://{host}:{port}")
    print("   AI Provider: IBM watsonx.ai (primary) | OpenAI (fallback)")
    print("   Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug)
