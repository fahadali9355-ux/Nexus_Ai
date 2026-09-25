"""Flask Web Dashboard for Aetheris Voice Assistant."""

import threading
from typing import Any, Dict
from flask import Flask, jsonify, render_template, request

from modules.state import state

app = Flask(__name__)


@app.route("/")
def index():
    """Serves the main web dashboard interface."""
    return render_template("index.html")


@app.route("/status")
@app.route("/api/status")
def get_status():
    """Returns the current real-time assistant status as JSON."""
    return jsonify(state.get_status())


@app.route("/history")
@app.route("/api/history")
def get_history():
    """Returns the running interaction history log as JSON."""
    limit = request.args.get("limit", type=int)
    return jsonify(state.get_history(limit=limit))


@app.route("/api/clear-history", methods=["POST"])
def clear_history():
    """Clears the history log."""
    state.clear_history()
    return jsonify({"success": True, "message": "History cleared successfully."})


@app.route("/api/test-command", methods=["POST"])
def test_command():
    """Allows simulating or triggering a text query directly through the pipeline.
    
    Captures and restores the previous assistant state to prevent race conditions
    with the ongoing continuous voice loop.
    """
    from main import identify_handler, route_and_process
    from modules.text_to_speech import speak_text

    data = request.get_json(silent=True) or {}
    user_text = data.get("query", "").strip()

    if not user_text:
        return jsonify({"error": "Empty query"}), 400

    # FIX 5: Save actual prior state to restore later without stomping ongoing loop state
    prior_state = state.get_status()
    prev_status = prior_state.get("status", "Idle / Listening for wake word")
    prev_module = prior_state.get("active_module", "Wake Word Engine")

    handler_name = identify_handler(user_text)
    state.set_status("Processing", active_module=handler_name, last_heard=user_text)

    try:
        response_text = route_and_process(user_text)
        if not response_text:
            response_text = "No response received from handler."
    except Exception as e:
        response_text = f"Error executing query: {e}"

    state.set_status("Speaking", active_module="Text-to-Speech", last_response=response_text)

    # Optional speech synthesis for simulator
    if data.get("speak", True):
        try:
            speak_text(response_text)
        except Exception as e:
            print(f"[Simulator TTS Warning] {e}")

    entry = state.add_history(
        heard=user_text,
        handler=handler_name,
        response=response_text,
        status="success",
    )

    # Restore the actual previous state from before the test command ran
    state.set_status(prev_status, active_module=prev_module)
    return jsonify({"success": True, "entry": entry})


# FIX 1: Remove background thread startup logic from app.py.
# Direct users to run main.py as the single unified entry point.
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  [AETHERIS NOTICE] Please start the application using:")
    print("      python main.py")
    print("=" * 60)
    print("  main.py is the single clean entry point that launches both")
    print("  the continuous voice assistant loop and the Flask dashboard.")
    print("  Running app.py directly is disabled to avoid port conflicts.\n")
