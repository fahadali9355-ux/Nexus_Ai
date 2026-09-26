import os
import re
import signal
import sys
import threading
import time
from typing import Optional, Tuple

from modules.audio_input import record_audio_with_silence_detection
from modules.speech_to_text import transcribe_audio
from modules.gemini_client import generate_response, route_to_action
from modules.text_to_speech import speak_text, stop_speech
from modules.task_executor import cleanup_browser
from modules.wake_word import listen_for_wake_word
from modules.fast_path import is_shutdown_command, try_local_fast_path
from modules.news_fetch import fetch_top_news
from modules.wikipedia_search import search_wikipedia
from modules.state import state


def shutdown_nexus(exit_code: int = 0) -> None:
    """Performs a comprehensive, graceful termination of Nexus and all subsystems.

    Stops audio playback/recording, cleans up browser automation sessions,
    uninitializes COM libraries, and cleanly exits the process without dangling background threads.
    """
    print("\n" + "=" * 60)
    print("      [SHUTDOWN] Terminating Nexus Voice Assistant...         ")
    print("=" * 60)
    try:
        state.set_status("Offline", active_module="Shutdown Manager")
    except Exception:
        pass

    try:
        stop_speech()
    except Exception as e:
        print(f"[Shutdown Warning] Audio stop error: {e}")

    try:
        cleanup_browser()
    except Exception as e:
        print(f"[Shutdown Warning] Browser cleanup error: {e}")

    try:
        import comtypes
        comtypes.CoUninitialize()
    except Exception:
        pass

    print("[SHUTDOWN] All subsystems cleanly released. Goodbye!\n")
    sys.stdout.flush()
    sys.stderr.flush()

    # Guarantee immediate and complete termination of all background threads and runtime handles
    os._exit(exit_code)


def _signal_handler(sig, frame):
    """OS Signal handler for SIGINT (Ctrl+C) and SIGTERM."""
    print("\n\n[SHUTDOWN] Termination signal received (Ctrl+C / SIGINT).")
    shutdown_nexus(exit_code=0)


# =====================================================================
# Wake Word Configuration (Vosk Keyword Spotting Engine)
# Supports: "Nexus", "Hey Nexus", and phonetic variants ("next us", "nexes", "nexis")
# =====================================================================
WAKE_WORDS = ["nexus", "hey nexus", "next us", "nexes", "nexis", "nexas"]

# =====================================================================
# Command Routing Heuristics (Fix B + Action Task Execution)
# =====================================================================

# Standalone intent keywords for the News Service
NEWS_INTENT_KEYWORDS = ["news", "headlines", "top stories", "breaking news", "current events"]

# Definitional prefixes intended for quick factual lookups
WIKI_PREFIXES = ["who is", "who was", "what is", "what was", "where is", "tell me about", "wiki", "wikipedia"]

# Verbs & interrogatives indicating generative / complex LLM reasoning tasks
GENERATIVE_OR_REASONING_VERBS = {
    "explain", "write", "generate", "how", "why", "code",
    "program", "debug", "compose", "compare", "summarize", "analyze",
    "solve", "draft", "elaborate", "teach", "help", "translate",
    "calculate", "discuss", "recommend", "suggest", "review", "detail"
}

# Unambiguous action trigger phrases that override generative/reasoning verbs
UNAMBIGUOUS_ACTION_PATTERNS = [
    r"\b(?:set|change|turn|adjust)\s+(?:the\s+)?volume\s+(?:to\s+)?\d+\b",
    r"\bvolume\s+to\s+\d+\b",
    r"\b(?:take\s+(?:a\s+)?screenshot|capture\s+(?:the\s+)?screen|screen\s*capture)\b",
    r"\b(?:lock\s+(?:the\s+|my\s+)?(?:computer|pc|screen|workstation))\b",
    r"\b(?:create|make)\s+(?:a\s+)?(?:text\s+)?file\s+(?:called|named)\s+[\w\.\-]+\b",
    r"\b(?:create|make|generate|build|draft|write)\s+(?:me\s+)?(?:a\s+|an\s+)?(?:word\s+document|pdf|pptx|powerpoint|presentation|slides?|document|assignment|doc|docx|report|paper)\b",
]

# Action-oriented command patterns for direct system task execution
ACTION_COMMAND_PATTERNS = [
    # Direct app launch/close or website opening/closing commands (e.g. 'open notepad', 'close youtube', 'close github tab')
    r"^(?:please\s+)?(?:open|launch|start|close|shut)\s+([a-zA-Z0-9_\.\-]+(?:\s+[a-zA-Z0-9_\.\-]+)?)$",
    # Website tab closing commands (e.g. 'close the github tab', 'close that youtube tab', 'close youtube tab')
    r"^(?:please\s+)?(?:close|shut)\s+(?:the\s+|that\s+)?(?:[\w\.\-]+\s+)?(?:tab|website|webpage)\b",
    r"^(?:please\s+)?(?:close|shut)\s+(?:the\s+|that\s+)?(?:tab\s+for\s+)?[\w\.\-]+\b",
    r"\b(?:close|shut)\s+(?:the\s+|that\s+)?(?:github|youtube|reddit|twitter|google|wikipedia|chrome|facebook|instagram)\s*(?:tab)?\b",
    # Volume control commands
    r"\b(?:set|change|turn|adjust)\s+(?:the\s+)?volume\s+(?:to\s+)?\d+\b",
    r"\bvolume\s+to\s+\d+\b",
    r"\b(?:mute|unmute)\s+(?:the\s+)?volume\b",
    r"\b(?:turn\s+up|turn\s+down)\s+(?:the\s+)?volume\b",
    # Lock computer commands
    r"\b(?:lock\s+(?:the\s+|my\s+)?(?:computer|pc|screen|workstation))\b",
    r"\block\s+(?:down\s+)?(?:pc|computer)\b",
    # Screenshot commands
    r"\b(?:take\s+(?:a\s+)?screenshot|capture\s+(?:the\s+)?screen|screen\s*capture)\b",
    # File creation commands
    r"\b(?:create|make)\s+(?:a\s+)?(?:text\s+)?file\b",
    r"\b(?:create|make)\s+(?:a\s+)?note\s+(?:called|named)\b",
    # Document & presentation generation commands
    r"\b(?:create|make|generate|build|draft|write)\s+(?:me\s+)?(?:a\s+|an\s+)?(?:word\s+document|pdf|pptx|powerpoint|presentation|slides?|document|assignment|doc|docx|report|paper)\b",
    r"^(?:make|create|generate)\s+(?:me\s+)?(?:a\s+|an\s+)?(?:pdf|document|presentation|slides?|word\s+doc)\s+on\b",
    # System info / battery / time queries
    r"^(?:what\s+time\s+is\s+it|what\s+is\s+the\s+time|current\s+time|what\s+date\s+is\s+it|today's\s+date|system\s+info(?:rmation)?|battery\s+(?:status|level|percent))\b",
    # Web navigation or specific search
    r"^(?:open|browse\s+to)\s+(?:website\s+)?(?:https?://|[a-zA-Z0-9\-]+\.(?:com|org|net|io|edu|gov))\b",
    r"^(?:search\s+(?:google\s+for|for|google))\s+.+",
]

# Lock computer specific patterns for confirmation safeguard
LOCK_PATTERNS = [
    r"\b(?:lock\s+(?:the\s+|my\s+)?(?:computer|pc|screen|workstation))\b",
    r"\block\s+(?:down\s+)?(?:pc|computer)\b",
]

# Short affirmative responses for pending confirmation resolution
AFFIRMATIVE_PHRASES = {
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "do it", "go ahead",
    "proceed", "please do", "confirm", "yes please", "yes do it", "haan",
    "ha", "theek hai", "ji haan", "bilkul", "yes do that", "do that", "yes create it",
    "yes make it", "yes generate it"
}

# Short negative / cancellation responses for pending confirmation resolution
NEGATIVE_PHRASES = {
    "no", "nope", "nah", "cancel", "stop", "don't", "dont", "do not",
    "never mind", "nevermind", "forget it", "nahi", "mat karo", "no thanks",
    "cancel it", "leave it"
}


def check_and_resolve_pending_action(user_text: str) -> Optional[str]:
    """Resolves short affirmative or negative confirmations against any active pending action.

    Prevents sending ambiguous phrases ('yes', 'do it', 'cancel') to Gemini with no context.
    """
    pending = state.get_pending_action()
    if not pending:
        return None

    clean = user_text.strip().lower().rstrip(".!?,;")
    tokens = clean.split()

    is_yes = clean in AFFIRMATIVE_PHRASES or (len(tokens) <= 3 and any(t in AFFIRMATIVE_PHRASES for t in tokens))
    is_no = clean in NEGATIVE_PHRASES or (len(tokens) <= 3 and any(t in NEGATIVE_PHRASES for t in tokens))

    if is_yes:
        state.clear_pending_action()
        action_name = pending.get("action") or pending.get("intent")
        topic = pending.get("topic", "")
        doc_type = pending.get("doc_type", "docx")
        print(f"-> [PENDING ACTION: CONFIRMED] Executing '{action_name}' for '{topic}' ({doc_type})...")

        if action_name == "create_assignment_document":
            from modules.document_generator import create_assignment_document
            return create_assignment_document(topic=topic, doc_type=doc_type)

        if action_name == "lock_computer":
            from modules.task_executor import lock_computer
            return lock_computer()

        return f"Proceeding with {action_name} for {topic}."

    if is_no:
        state.clear_pending_action()
        print(f"-> [PENDING ACTION: CANCELLED] User cancelled pending action '{pending.get('action')}'.")
        return "Cancelled. I won't proceed with that request."

    # If the user issued an unrelated, longer new command, clear the stale pending action
    state.clear_pending_action()
    return None


def is_unambiguous_action(lower_text: str) -> bool:
    """Checks if text contains an explicit, unambiguous action command that overrides generative phrasing."""
    return any(re.search(pat, lower_text) for pat in UNAMBIGUOUS_ACTION_PATTERNS)


def is_action_command(lower_text: str) -> bool:
    """Checks if text matches direct, tightened action command patterns."""
    return any(re.search(pat, lower_text) for pat in ACTION_COMMAND_PATTERNS)


def is_lock_command(lower_text: str) -> bool:
    """Checks if a user command specifically requests locking the computer."""
    return any(re.search(pat, lower_text) for pat in LOCK_PATTERNS)


def parse_intent(user_text: str) -> Tuple[str, Optional[str]]:
    """Analyzes user text and returns destination handler ('Shutdown', 'Action', 'Gemini', 'Wikipedia', 'News') and extracted topic.

    Routing Priority Order:
      0. Voice Stop / Exit / Sleep commands -> Shutdown
      1. Generative / Reasoning Verbs ('explain', 'write', 'how', 'why', etc.)
         -> Sent to Gemini conversational AI, UNLESS an unambiguous action trigger phrase
            (e.g., 'take a screenshot', 'lock the computer', 'set volume to X') is present.
      2. Clear Action Commands (direct app open/launch/close, volume change, screenshot, lock, file creation)
         -> Sent to Gemini Function Calling tool router (route_to_action).
      3. News Service Intent ('news', 'headlines', 'top stories', etc.)
         -> Sent to NewsAPI fetcher for live headlines.
      4. Wikipedia Definitional Search ('who is X', 'what is X', 'where is X', 'wiki X')
         -> Sent to Wikipedia ONLY if X is a short noun phrase (1 to 5 words).
      5. Default Fallback
         -> All general inquiries, reasoning, conversational chat route to Gemini AI.
    """
    cleaned = user_text.strip()
    lower_text = cleaned.lower()

    if not cleaned:
        return ("Gemini", None)

    # Priority 0: Explicit Voice Shutdown / Stop command
    if is_shutdown_command(cleaned):
        return ("Shutdown", None)

    # Extract individual alphanumeric word tokens
    tokens = re.findall(r"\b[a-zA-Z0-9']+\b", lower_text)
    token_set = set(tokens)

    # -------------------------------------------------------------
    # Priority 1: Generative / reasoning verbs -> Gemini
    # (UNLESS sentence contains an unambiguous action trigger)
    # Examples: "explain how volume controls work" -> Gemini
    #           "write a note about how to open a bank account" -> Gemini
    #           "how do I start a business" -> Gemini
    # -------------------------------------------------------------
    if any(verb in token_set for verb in GENERATIVE_OR_REASONING_VERBS):
        if is_unambiguous_action(lower_text):
            return ("Action", None)
        return ("Gemini", None)

    # -------------------------------------------------------------
    # Priority 2: Clear action commands (tightened command patterns)
    # Examples: "open notepad", "set volume to 50", "take a screenshot", "lock computer"
    # -------------------------------------------------------------
    if is_action_command(lower_text):
        return ("Action", None)

    # -------------------------------------------------------------
    # Priority 3: News Service Intent
    # Examples: "give me the latest news", "what are the top headlines"
    # -------------------------------------------------------------
    if any(keyword in lower_text for keyword in NEWS_INTENT_KEYWORDS):
        return ("News", None)

    # -------------------------------------------------------------
    # Priority 4: Wikipedia Factual / Definitional Search
    # Examples: "who is Albert Einstein", "what is photosynthesis", "wiki Ada Lovelace"
    # -------------------------------------------------------------
    for prefix in WIKI_PREFIXES:
        if lower_text.startswith(prefix):
            candidate_topic = cleaned[len(prefix):].strip(" ?:.,;!")
            candidate_words = candidate_topic.split()

            # Only concise noun phrases (1 to 5 words) route to Wikipedia
            if 1 <= len(candidate_words) <= 5:
                return ("Wikipedia", candidate_topic)
            else:
                return ("Gemini", None)

    # Also handle standalone "wiki <topic>" prefix/word
    if "wiki " in lower_text:
        parts = re.split(r"\bwiki\b", cleaned, flags=re.IGNORECASE)
        if len(parts) > 1:
            candidate_topic = parts[1].strip(" ?:.,;!")
            if 1 <= len(candidate_topic.split()) <= 5:
                return ("Wikipedia", candidate_topic)

    # -------------------------------------------------------------
    # Priority 5: Default Fallback to Gemini AI
    # -------------------------------------------------------------
    return ("Gemini", None)


def identify_handler(user_text: str) -> str:
    """Returns the module identifier ('Shutdown', 'Action', 'News', 'Wikipedia', or 'Gemini') that will handle the query."""
    handler, _ = parse_intent(user_text)
    return handler


def route_and_process(user_text: str) -> str:
    """Routes the user query based on heuristic priority to Action Executor, News, Wikipedia, or Gemini AI."""
    # Priority -1: Short-term pending action confirmation resolution
    pending_result = check_and_resolve_pending_action(user_text)
    if pending_result is not None:
        return pending_result

    handler, topic = parse_intent(user_text)

    # Route 0: Voice Shutdown
    if handler == "Shutdown" or is_shutdown_command(user_text):
        print(f"-> [Routing Path: Voice Shutdown / Exit for '{user_text}']")
        return "Shutting down Nexus. Goodbye!"

    # Route 1: Action Task Execution (Local Fast-Path with Gemini Fallback)
    elif handler == "Action":
        # Check instant local fast-path for deterministic commands
        fast_result = try_local_fast_path(user_text)
        if fast_result is not None:
            print(f"-> [Routing Path: Local Fast-Path Executor (Instant) for '{user_text}']")
            return fast_result

        # Ambiguous / complex actions fall through to Gemini function calling
        print(f"-> [Routing Path: Action Task Executor (Gemini Tools) for '{user_text}']")
        return route_to_action(user_text)

    # Route 2: News Service
    elif handler == "News":
        print("-> [Routing Path: News Service]")
        return fetch_top_news(limit=3)

    # Route 3: Wikipedia Search
    elif handler == "Wikipedia":
        search_query = topic if topic else user_text
        print(f"-> [Routing Path: Wikipedia Search ('{search_query}')]")
        return search_wikipedia(search_query)

    # Route 4: Default Gemini AI
    else:
        print("-> [Routing Path: Gemini AI]")
        return generate_response(user_text) or "Sorry, I could not process your query right now."


# =====================================================================
# Continuous Daemon Loop (Fix A, B, C)
# =====================================================================

def run_voice_loop() -> None:
    """Executes the continuous end-to-end voice assistant daemon loop."""
    print("\n========================================================")
    print("        NEXUS VOICE ASSISTANT - CONTINUOUS DAEMON       ")
    print("========================================================")
    print("Wake Word: 'Nexus' / 'Hey Nexus' | Status: Active | Dashboard: http://127.0.0.1:5000\n")

    # Initialize COM library once at daemon startup for Windows audio and system controls
    try:
        import comtypes
        comtypes.CoInitialize()
        print("[COM] Windows COM library initialized on voice daemon thread.")
    except Exception as com_err:
        print(f"[COM] COM initialization note: {com_err}")

    while True:
        try:
            # -------------------------------------------------------------
            # Stage 1: Wake Word Listening (Vosk Offline Keyword Spotter)
            # -------------------------------------------------------------
            state.set_status("Idle / Listening for wake word", active_module="Wake Word Engine")
            print("\n--------------------------------------------------------")
            print("[LISTENING] Listening continuously for wake word 'Nexus' (or 'Hey Nexus')...")

            try:
                wake_detected = listen_for_wake_word(wake_word=WAKE_WORDS)
            except KeyboardInterrupt:
                raise
            except Exception as wake_err:
                print(f"[ERROR: WAKE WORD] Exception in wake word listener: {wake_err}")
                time.sleep(1.0)
                continue

            if not wake_detected:
                print("[WAKE WORD] Listener returned False (stream reset/retry). Re-entering listener loop...")
                time.sleep(0.5)
                continue

            print("[WAKE WORD DETECTED] Wake word detected! Transitioning to command recording...")

            # -------------------------------------------------------------
            # Stage 2: Audio Recording (Fix A: Variable-Length Silence Detection)
            # -------------------------------------------------------------
            state.set_status("Listening for command", active_module="Audio Recorder")
            print("[RECORDING] Capturing spoken command with dynamic silence detection...")
            try:
                audio_file = record_audio_with_silence_detection(
                    output_filename="temp_input.wav",
                    min_duration=1.0,
                    max_duration=15.0,
                    silence_duration=1.2,
                )
                if not audio_file:
                    print("[ERROR: RECORDING] Failed to capture audio recording.")
                    speak_text("Sorry, I couldn't access your microphone.")
                    state.set_status("Error / Recovering", active_module="Audio Recorder")
                    time.sleep(1.0)
                    continue
            except KeyboardInterrupt:
                raise
            except Exception as rec_err:
                print(f"[ERROR: RECORDING] Exception during audio recording: {rec_err}")
                speak_text("An audio recording error occurred.")
                state.set_status("Error / Recovering", active_module="Audio Recorder")
                time.sleep(1.0)
                continue

            # -------------------------------------------------------------
            # Stage 3: Speech-to-Text Transcription
            # -------------------------------------------------------------
            state.set_status("Processing", active_module="Speech-to-Text")
            print("[TRANSCRIBING] Transcribing audio with Google Speech Recognition...")
            try:
                user_text = transcribe_audio(audio_file)
                if not user_text or not user_text.strip():
                    print("[TRANSCRIBING] Unrecognized speech or silence detected.")
                    speak_text("Sorry, I didn't catch that. Could you please repeat?")
                    state.add_history(
                        heard="[Unrecognized Speech / Silence]",
                        handler="Speech-to-Text",
                        response="Sorry, I didn't catch that. Could you please repeat?",
                        status="warning",
                    )
                    continue
                print(f"[TRANSCRIBING] Transcribed user text: \"{user_text}\"")
            except KeyboardInterrupt:
                raise
            except Exception as stt_err:
                print(f"[ERROR: TRANSCRIBING] Exception during speech-to-text: {stt_err}")
                speak_text("Sorry, I had trouble processing your speech.")
                state.add_history(
                    heard="[Transcription Error]",
                    handler="Speech-to-Text",
                    response="Sorry, I had trouble processing your speech.",
                    status="error",
                )
                continue

            # -------------------------------------------------------------
            # Stage 4: Command Routing & Processing
            # -------------------------------------------------------------
            # Check for Voice Shutdown / Stop Commands
            if is_shutdown_command(user_text):
                print(f"\n[SHUTDOWN] Voice-triggered stop command recognized: \"{user_text}\"")
                state.set_status("Shutting down", active_module="Core Daemon", last_heard=user_text)
                print("[SPEAKING] Speaking shutdown confirmation aloud...")
                try:
                    speak_text("Shutting down Nexus. Goodbye!")
                except Exception as tts_err:
                    print(f"[Shutdown Warning] TTS confirmation error: {tts_err}")

                state.add_history(
                    heard=user_text,
                    handler="Shutdown",
                    response="Shutting down Nexus. Goodbye!",
                    status="success",
                )
                shutdown_nexus(exit_code=0)
                return

            handler_name = identify_handler(user_text)
            state.set_status("Processing", active_module=handler_name, last_heard=user_text)
            print(f"[ROUTING] Routing query to [{handler_name}]...")
            try:
                # Security Safeguard: High-risk action confirmation for lock_computer
                if handler_name == "Action" and is_lock_command(user_text.lower()):
                    print("[SECURITY SAFEGUARD] High-risk action detected ('lock_computer'). Requesting verbal confirmation...")
                    state.set_status("Awaiting Confirmation", active_module="Security Safeguard", last_heard=user_text)
                    speak_text("Are you sure you want to lock the computer? Say yes to confirm.")

                    state.set_status("Listening for confirmation", active_module="Audio Recorder")
                    print("[CONFIRMATION] Capturing confirmation response...")
                    confirm_audio = record_audio_with_silence_detection(
                        output_filename="temp_confirm.wav",
                        min_duration=0.5,
                        max_duration=6.0,
                        silence_duration=1.0,
                    )

                    confirmed = False
                    if confirm_audio:
                        confirm_text = transcribe_audio(confirm_audio)
                        print(f"[CONFIRMATION] Transcribed confirmation speech: \"{confirm_text}\"")
                        if confirm_text:
                            lower_confirm = confirm_text.lower()
                            if any(w in lower_confirm for w in ["yes", "confirm", "yeah", "yep", "sure", "proceed"]):
                                confirmed = True

                    if confirmed:
                        print("[CONFIRMATION] User confirmed lock. Executing lock_computer()...")
                        from modules.task_executor import lock_computer
                        response_text = lock_computer()
                    else:
                        print("[CONFIRMATION] User did not confirm or cancelled. Lock cancelled.")
                        response_text = "Lock cancelled."
                else:
                    response_text = route_and_process(user_text)

                if not response_text or not response_text.strip():
                    print(f"[ERROR: ROUTING] Handler '{handler_name}' returned empty response.")
                    response_text = "Sorry, I couldn't process your request right now."
                print(f"[ROUTING] Handler [{handler_name}] response: {response_text}")
            except KeyboardInterrupt:
                raise
            except Exception as route_err:
                print(f"[ERROR: ROUTING] Exception while processing query: {route_err}")
                response_text = "An error occurred while processing your request."

            # -------------------------------------------------------------
            # Stage 5: Text-to-Speech Output
            # -------------------------------------------------------------
            state.set_status("Speaking", active_module="Text-to-Speech", last_response=response_text)
            print(f"[SPEAKING] Speaking response aloud using Piper Neural TTS...")
            try:
                speak_success = speak_text(response_text)
                if not speak_success:
                    print("[WARNING: SPEAKING] Text-to-speech output returned failure status.")
            except KeyboardInterrupt:
                raise
            except Exception as tts_err:
                print(f"[ERROR: SPEAKING] Exception during speech synthesis: {tts_err}")

            # Record completed interaction into state history
            state.add_history(
                heard=user_text,
                handler=handler_name,
                response=response_text,
                status="success",
            )
            print("[CYCLE COMPLETED] Cycle finished. Returning to wake word listener.")

        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Nexus daemon loop interrupted by user (KeyboardInterrupt).")
            shutdown_nexus(exit_code=0)
            break
        except Exception as loop_err:
            print(f"[PIPELINE EXCEPTION] Unexpected error in daemon cycle: {loop_err}")
            state.set_status("Error / Recovering", active_module="Core Daemon")
            time.sleep(1.0)


def start_flask_server(host: str = "127.0.0.1", port: int = 5000) -> None:
    """Starts the Flask web dashboard server."""
    import logging
    # Suppress verbose HTTP access logs in console for clean terminal output
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    from app import app
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Register OS signal handlers for graceful shutdown on Ctrl+C / SIGINT / SIGTERM
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    # Start web dashboard in a background daemon thread
    dashboard_thread = threading.Thread(target=start_flask_server, daemon=True)
    dashboard_thread.start()
    print("-> Web Dashboard live at: http://127.0.0.1:5000")

    # Run the continuous voice assistant loop in main thread
    try:
        run_voice_loop()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by user.")
        shutdown_nexus(exit_code=0)
    finally:
        shutdown_nexus(exit_code=0)

