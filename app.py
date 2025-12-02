# app.py
"""
Streamlit Voice Synthesizer (Python 3.13 Compatible)
====================================================

Instructions:
1. Create a virtual environment:
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
2. Install requirements:
   pip install -r requirements.txt
3. Run the app:
   streamlit run app.py
4. Uploaded files saved in 'uploads/', generated audio in 'generated/'

Note: Uses pyttsx3 offline TTS. No speaker cloning.
Use this system only for lawful, consensual use. Written consent required.
"""

import os
import csv
import datetime
import streamlit as st
from pathlib import Path
from werkzeug.utils import secure_filename
import pyttsx3

# Configuration
UPLOAD_FOLDER = "uploads"
GENERATED_FOLDER = "generated"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"wav", "mp3"}
CONSENT_LOG = "consent_log.csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 150)
tts_engine.setProperty("volume", 1.0)

# Utility functions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def prepend_marker(text):
    return "SYNTHETIC VOICE — GENERATED. " + text

def log_consent(speaker_name, requester_email, filename, ip):
    header = ["timestamp", "requester_email", "speaker_name", "uploaded_filename", "client_ip"]
    timestamp = datetime.datetime.utcnow().isoformat()
    write_header = not Path(CONSENT_LOG).exists()
    with open(CONSENT_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)
        writer.writerow([timestamp, requester_email, speaker_name, filename, ip])

def generate_audio(text, output_path):
    tts_engine.save_to_file(text, output_path)
    tts_engine.runAndWait()

# Streamlit UI
st.title("Voice Synthesizer")
st.markdown("⚠️ **Warning:** Cloning voices without explicit written consent is illegal and prohibited.")

uploaded_file = st.file_uploader("Upload reference audio (wav/mp3, max 10MB):", type=list(ALLOWED_EXTENSIONS))
text_to_synthesize = st.text_area("Text to synthesize (max 500 chars):", max_chars=500)
speaker_name = st.text_input("Speaker Name:")
requester_email = st.text_input("Your Email:")
consent = st.checkbox("I have written consent from the speaker.")
not_public = st.checkbox("I confirm the speaker is NOT a public figure.")

if st.button("Generate"):
    if uploaded_file is None:
        st.error("Please upload a reference audio file.")
    elif not allowed_file(uploaded_file.name):
        st.error("Invalid file type. Only wav/mp3 allowed.")
    elif len(text_to_synthesize.strip()) == 0:
        st.error("Please enter text to synthesize.")
    elif not consent:
        st.error("Consent checkbox must be checked.")
    elif not not_public:
        st.error("Cannot process public figure voices.")
    elif speaker_name.strip() == "" or requester_email.strip() == "":
        st.error("Please fill in speaker name and your email.")
    else:
        try:
            filename = secure_filename(uploaded_file.name)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            log_consent(speaker_name, requester_email, filename, st.session_state.get("client_ip", "N/A"))
            output_path = os.path.join(GENERATED_FOLDER, f"{filename}_synth.wav")
            final_text = prepend_marker(text_to_synthesize)
            generate_audio(final_text, output_path)
            st.success("Audio generated successfully!")
            st.download_button("Download Generated Audio", output_path, file_name=f"{filename}_synth.wav")
        except Exception as e:
            st.error(f"Error during synthesis: {e}")
