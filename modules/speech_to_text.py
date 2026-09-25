"""Module for converting speech audio files into text using SpeechRecognition."""

from typing import Optional
import speech_recognition as sr


def transcribe_audio(audio_file_path: str = "test_recording.wav") -> Optional[str]:
    """Transcribes a .wav audio file into text using Google Web Speech API.

    Args:
        audio_file_path (str): Path to the WAV audio file.

    Returns:
        Optional[str]: Transcribed text string, or None if speech was unintelligible or request failed.
    """
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(audio_file_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data)
        return text

    except sr.UnknownValueError:
        print("[Error: Speech-to-Text] Speech unrecognized or silent.")
        return None
    except sr.RequestError as err:
        print(f"[Error: Speech-to-Text] Network or API failure contacting Google Speech Recognition: {err}")
        return None
    except FileNotFoundError as err:
        print(f"[Error: Speech-to-Text] Audio file not found: {err}")
        return None
    except Exception as err:
        print(f"[Error: Speech-to-Text] Unexpected transcription error: {err}")
        return None


if __name__ == "__main__":
    result = transcribe_audio("test_recording.wav")
    print(f"Transcription result: {result}")
