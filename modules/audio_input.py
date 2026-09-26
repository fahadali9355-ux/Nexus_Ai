import os
import time
from typing import List, Optional
from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

# Load environment variables
load_dotenv()


def record_audio(
    output_filename: str = "test_recording.wav",
    duration: float = 5.0,
    sample_rate: int = 44100,
    channels: int = 1,
    device: Optional[int] = None,
) -> Optional[str]:
    """Records audio from the default microphone for a fixed duration and saves it to a .wav file.
    
    (Maintained for backward compatibility).

    Args:
        output_filename (str): Path to output WAV file.
        duration (float): Recording duration in seconds.
        sample_rate (int): Sampling rate in Hz (samples per second).
        channels (int): Number of audio channels (1 for mono, 2 for stereo).

    Returns:
        Optional[str]: Path to output WAV file if successful, or None if recording failed.
    """
    try:
        print(f"Recording for {duration} seconds... Speak into your microphone.")
        num_frames = int(duration * sample_rate)
        recording = sd.rec(
            num_frames,
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
        )
        sd.wait()  # Wait until the recording is finished
        print("Recording completed.")

        wavfile.write(output_filename, sample_rate, recording)
        print(f"Saved recording to '{output_filename}'.")
        return output_filename

    except KeyboardInterrupt:
        try:
            sd.stop()
        except Exception:
            pass
        raise
    except sd.PortAudioError as err:
        print(f"[Error: Audio Input] PortAudio microphone error: {err}")
        return None
    except OSError as err:
        print(f"[Error: Audio Input] File system error writing WAV file: {err}")
        return None
    except Exception as err:
        print(f"[Error: Audio Input] Unexpected recording failure: {err}")
        return None


def record_audio_with_silence_detection(
    output_filename: str = "temp_input.wav",
    min_duration: float = 1.0,
    max_duration: float = 15.0,
    silence_duration: float = 1.2,
    energy_threshold: float = 350.0,
    sample_rate: int = 44100,
    channels: int = 1,
    device: Optional[int] = None,
) -> Optional[str]:
    """Records audio with dynamic silence detection, stopping when the user finishes speaking.

    Features:
      1. Starts recording immediately upon call.
      2. Dynamically calibrates ambient noise floor.
      3. Automatically stops after ~1.0-1.5s of continuous silence following speech.
      4. Hard maximum cap (15.0s) ensures it never records indefinitely.
      5. Minimum recording floor (1.0s) prevents premature cutoffs.

    Args:
        output_filename (str): Path to output WAV file.
        min_duration (float): Minimum recording duration in seconds before silence cutoff applies.
        max_duration (float): Hard maximum cap in seconds.
        silence_duration (float): Consecutive seconds of silence after speech to trigger stop.
        energy_threshold (float): Minimum RMS energy threshold to classify as speech.
        sample_rate (int): Audio sampling rate in Hz (default 44100).
        channels (int): Mono (1) or Stereo (2).
        device (Optional[int]): Input audio device index (default from env MIC_DEVICE_INDEX or system default).

    Returns:
        Optional[str]: Path to saved WAV file if successful, or None on failure.
    """
    if device is None:
        env_dev = os.getenv("MIC_DEVICE_INDEX")
        if env_dev is not None and env_dev.strip().isdigit():
            device = int(env_dev.strip())

    chunk_duration = 0.05  # 50ms chunks for responsive volume monitoring
    chunk_size = int(sample_rate * chunk_duration)
    audio_frames: List[np.ndarray] = []
    initial_rms_samples: List[float] = []

    print(f"[Audio Recorder] Listening for command (Max: {max_duration}s, Silence Cutoff: {silence_duration}s)...")

    start_time = time.time()
    silence_start: Optional[float] = None
    speech_detected = False
    effective_threshold = energy_threshold

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            blocksize=chunk_size,
            device=device,
        ) as stream:
            while True:
                chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    pass  # Audio buffer overflow handled gracefully

                audio_frames.append(chunk.copy())
                elapsed = time.time() - start_time

                # Calculate Root Mean Square (RMS) volume of the chunk
                chunk_float = chunk.astype(np.float64)
                rms = float(np.sqrt(np.mean(chunk_float ** 2)))

                # Calibrate ambient noise during initial 200ms
                if elapsed < 0.20:
                    initial_rms_samples.append(rms)
                    if initial_rms_samples:
                        ambient_avg = float(np.mean(initial_rms_samples))
                        effective_threshold = max(energy_threshold, ambient_avg * 1.6)

                # Check if current chunk contains active speech
                if rms >= effective_threshold:
                    if not speech_detected:
                        speech_detected = True
                        print(f"-> [Voice Detected] User started speaking (RMS: {rms:.1f} >= {effective_threshold:.1f}).")
                    silence_start = None  # Reset silence timer on active voice
                else:
                    # In silence / below speech threshold
                    if speech_detected:
                        if elapsed >= min_duration:
                            if silence_start is None:
                                silence_start = time.time()
                            elif (time.time() - silence_start) >= silence_duration:
                                print(f"-> [Silence Detected] {silence_duration:.1f}s of silence after speech. Finalizing recording ({elapsed:.1f}s total).")
                                break
                    else:
                        # User has not spoken yet; timeout if complete silence persists for 6 seconds
                        if elapsed >= 6.0:
                            print(f"-> [No Speech] Initial silence timeout reached ({elapsed:.1f}s). Ending recording.")
                            break

                # Enforce hard maximum duration cap
                if elapsed >= max_duration:
                    print(f"-> [Max Duration] Reached hard recording cap ({max_duration}s). Finalizing recording.")
                    break

        if not audio_frames:
            print("[Audio Recorder Error] No audio frames captured.")
            return None

        # Concatenate chunks into a single numpy array and write WAV
        recorded_audio = np.concatenate(audio_frames, axis=0)
        wavfile.write(output_filename, sample_rate, recorded_audio)
        total_duration = len(recorded_audio) / sample_rate
        print(f"[Audio Recorder] Saved {total_duration:.2f}s recording to '{output_filename}'.")
        return output_filename

    except KeyboardInterrupt:
        try:
            sd.stop()
        except Exception:
            pass
        raise
    except sd.PortAudioError as err:
        print(f"[Audio Recorder Error] PortAudio device exception: {err}")
        return None
    except OSError as err:
        print(f"[Audio Recorder Error] Filesystem error saving audio file: {err}")
        return None
    except Exception as err:
        print(f"[Audio Recorder Error] Unexpected recording exception: {err}")
        return None


if __name__ == "__main__":
    print("Testing variable-length recording with silence detection (speak a phrase, then pause)...")
    res = record_audio_with_silence_detection(output_filename="test_silence_recording.wav")
    print(f"Recording result: {res}")
