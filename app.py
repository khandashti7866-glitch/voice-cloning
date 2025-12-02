# app.py
"""
Flask Voice Cloning App
=======================

Instructions:
1. Create virtual environment:
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
2. Install requirements:
   pip install -r requirements.txt
3. Run the app:
   python app.py
4. Uploaded files are saved in 'uploads/' and generated files are downloadable from the same directory.

Open-source libraries used:
- Flask
- TTS (Coqui TTS)
- Resemblyzer
- numpy, scipy, soundfile, werkzeug

Use this system only for lawful, consensual use. Operator must obtain written consent.
"""

import os
import csv
import datetime
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pathlib import Path
import numpy as np
import soundfile as sf
from TTS.api import TTS
from resemblyzer import VoiceEncoder, preprocess_wav

UPLOAD_FOLDER = "uploads"
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"wav", "mp3"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("generated", exist_ok=True)
CONSENT_LOG = "consent_log.csv"

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = "replace_with_secure_random_key"

# Load pre-trained models (paths can be changed here)
try:
    tts = TTS(model_name="tts_models/en/vctk/vits")  # Change model here if desired
    encoder = VoiceEncoder()  # Resemblyzer encoder
except Exception as e:
    print("Error loading models:", e)
    raise

# HTML Template
HTML_TEMPLATE = """
<!doctype html>
<title>Voice Cloning App</title>
<h2 style="color:red;">WARNING: Cloning voices without explicit written consent is illegal and prohibited.</h2>
<form method=post enctype=multipart/form-data>
  <label>Upload reference audio (wav/mp3, max 10MB):</label><br>
  <input type=file name=file required><br><br>
  
  <label>Text to synthesize (max 500 chars):</label><br>
  <textarea name=text rows=4 cols=50 maxlength=500 required></textarea><br><br>
  
  <label>Speaker Name:</label><br>
  <input type=text name=speaker_name required><br><br>
  
  <label>Your Email:</label><br>
  <input type=email name=requester_email required><br><br>
  
  <input type=checkbox name=consent value="yes" required> I have written consent from the speaker.<br>
  <input type=checkbox name=not_public value="yes" required> I confirm the speaker is NOT a public figure.<br><br>
  
  <input type=submit value="Generate">
</form>

{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color:red;">
    {% for message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

{% if generated_file %}
<p>Generated file ready: <a href="{{ url_for('download_file', filename=generated_file) }}">{{ generated_file }}</a></p>
{% endif %}
"""

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

@app.route("/", methods=["GET", "POST"])
def index():
    generated_file = None
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("Invalid file type. Only wav/mp3 allowed.")
            return redirect(request.url)
        text = request.form.get("text", "")
        if len(text) == 0 or len(text) > 500:
            flash("Text is required and must be <= 500 chars.")
            return redirect(request.url)
        consent = request.form.get("consent")
        not_public = request.form.get("not_public")
        if consent != "yes":
            flash("Consent checkbox must be checked.")
            return redirect(request.url)
        if not_public != "yes":
            flash("Cannot process public figure voices.")
            return redirect(request.url)
        speaker_name = request.form.get("speaker_name")
        requester_email = request.form.get("requester_email")
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        log_consent(speaker_name, requester_email, filename, request.remote_addr)

        try:
            # Load reference audio
            wav = preprocess_wav(file_path)
            embed = encoder.embed_utterance(wav)
            # Prepend marker
            final_text = prepend_marker(text)
            # Generate audio
            output_path = os.path.join("generated", f"{filename}_synth.wav")
            tts.tts_to_file(text=final_text, speaker_wav=file_path, file_path=output_path)
            generated_file = os.path.basename(output_path)
            flash("Processing Done.")
        except Exception as e:
            flash(f"Error during synthesis: {e}")
    return render_template_string(HTML_TEMPLATE, generated_file=generated_file)

@app.route("/generated/<filename>")
def download_file(filename):
    return send_from_directory("generated", filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
