"""Module for converting text responses into spoken audio using pyttsx3."""

import pyttsx3


def speak_text(text: str) -> bool:
    """Converts a text string to speech and plays it aloud using pyttsx3.

    Args:
        text (str): Text string to be spoken aloud.

    Returns:
        bool: True if speech synthesis succeeded, False otherwise.
    """
    if not text or not text.strip():
        return False

    try:
        # Initialize pyttsx3 engine
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except RuntimeError as err:
        print(f"[Error: Text-to-Speech] Engine runtime exception: {err}")
        return False
    except Exception as err:
        print(f"[Error: Text-to-Speech] Audio output hardware/driver error: {err}")
        return False


if __name__ == "__main__":
    test_sentence = "Hello! This is a test of the text to speech module."
    print(f"Speaking: '{test_sentence}'")
    speak_text(test_sentence)
