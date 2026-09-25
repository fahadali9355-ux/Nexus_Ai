# Manual Test Checklist & Notes

This document provides a manual test plan for verifying the Aetheris voice assistant pipeline under various real-world conditions.

---

## Test Cases

### 1. Normal Question Flow
- **Goal:** Verify end-to-end functionality under normal operating conditions with clear voice input.
- **Steps:**
  1. Set a valid `GEMINI_API_KEY` in `.env`.
  2. Run `python main.py`.
  3. Speak a clear question into the microphone (e.g., *"What is the distance from Earth to the Moon?"*).
- **Expected Result:**
  - Audio records for 5 seconds.
  - Speech is transcribed correctly in Stage 2.
  - Gemini returns a concise response in Stage 3.
  - Response is spoken aloud cleanly in Stage 4.
- **Status:** `[ ] Pending`

---

### 2. Silence / No Speech
- **Goal:** Verify pipeline handling when no speech is uttered during the recording window.
- **Steps:**
  1. Run `python main.py`.
  2. Remain completely silent for the 5-second recording duration.
- **Expected Result:**
  - Stage 2 outputs `[Error: Speech-to-Text] Speech unrecognized or silent.`
  - Pipeline speaks: *"Sorry, I didn't catch that. Could you please repeat?"*
  - Pipeline exits cycle gracefully without crashing.
- **Status:** `[ ] Pending`

---

### 3. Network Disconnected During Gemini Call
- **Goal:** Verify pipeline handling when internet connectivity is unavailable during API request.
- **Steps:**
  1. Disconnect Wi-Fi or internet connection.
  2. Run `python main.py` and speak a question.
- **Expected Result:**
  - Speech transcription succeeds or fails gracefully.
  - Stage 3 catches connection error (`[Error: Gemini API] Network connection...`).
  - Pipeline speaks fallback: *"Sorry, I couldn't reach the AI service right now."*
  - Program exits gracefully without crashing.
- **Status:** `[ ] Pending`

---

### 4. Very Long Spoken Input
- **Goal:** Verify behavior when user speaks continuously past the 5-second recording limit.
- **Steps:**
  1. Run `python main.py`.
  2. Speak continuously for 10+ seconds without pausing.
- **Expected Result:**
  - Audio input truncates cleanly at 5.0 seconds.
  - Speech captured in the 5-second window is transcribed and sent to Gemini.
  - No buffer overflow or pipeline crash occurs.
- **Status:** `[ ] Pending`

---

### 5. Background Noise
- **Goal:** Verify transcription robustness when ambient noise (clapping, music, typing) is present.
- **Steps:**
  1. Play background music or make ambient noise.
  2. Run `python main.py` and speak a short prompt.
- **Expected Result:**
  - Either speech is transcribed despite noise, or caught cleanly as unrecognized speech without crashing.
- **Status:** `[ ] Pending`

---

## Test Execution Notes
*(Add feedback or observations here after running tests)*
