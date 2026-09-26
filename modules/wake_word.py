"""Wake-Word detection module for Nexus assistant using Vosk speech recognition engine."""

from modules.wake_word_vosk import (
    DEFAULT_WAKE_WORDS,
    get_last_detected_keyword,
    get_last_partial_transcript,
    get_vosk_model,
    listen_for_wake_word,
    listen_for_wake_word_vosk,
)

__all__ = [
    "DEFAULT_WAKE_WORDS",
    "get_last_detected_keyword",
    "get_last_partial_transcript",
    "get_vosk_model",
    "listen_for_wake_word",
    "listen_for_wake_word_vosk",
]

if __name__ == "__main__":
    print("Testing continuous background listening for 'Nexus'...")
    detected = listen_for_wake_word(listen_timeout=15.0, debug=True)
    print(f"Wake word detected result: {detected}")
