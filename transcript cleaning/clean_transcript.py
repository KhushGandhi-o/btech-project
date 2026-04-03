import spacy
import json
import re

nlp = spacy.load("en_core_web_sm")

FILLERS = {"uh", "um", "hmm", "like", "okay", "right", "so", "basically"}

# Keywords that suggest who is speaking
DOCTOR_KEYWORDS = [
    "prescribe", "prescription", "temperature", "pulse", "diagnosis",
    "looks like", "i will", "please", "drink", "take rest", "mg",
    "degrees", "do you", "any vomiting", "any dizziness", "infection",
    "medication", "tablet", "recommend", "advise", "test", "examine"
]

PATIENT_KEYWORDS = [
    "i have", "i feel", "i am", "i've", "my", "pain", "headache",
    "fever", "tired", "vomiting", "dizzy", "since", "past", "days",
    "no vomiting", "a little", "slightly", "suffering"
]

def detect_speaker(text):
    text_lower = text.lower()

    doctor_score = sum(1 for kw in DOCTOR_KEYWORDS if kw in text_lower)
    patient_score = sum(1 for kw in PATIENT_KEYWORDS if kw in text_lower)

    # Questions are usually asked by the doctor
    if text.strip().endswith("?"):
        doctor_score += 2

    # "I have / I feel" strongly suggests patient
    if re.search(r"\bi have\b|\bi feel\b|\bi am\b", text_lower):
        patient_score += 2

    if doctor_score > patient_score:
        return "Doctor"
    elif patient_score > doctor_score:
        return "Patient"
    else:
        return "Unknown"  # fallback if scores are equal

def clean_text(text):
    doc = nlp(text.strip())
    tokens = [
        token.text for token in doc
        if token.text.lower() not in FILLERS
        and not token.is_space
    ]
    return " ".join(tokens).strip()

def clean_transcript(segments):
    cleaned = []
    for seg in segments:
        cleaned_text = clean_text(seg["text"])
        if cleaned_text:
            speaker = detect_speaker(cleaned_text)
            cleaned.append({
                "start": seg["start"],
                "end": seg["end"],
                "speaker": speaker,
                "text": cleaned_text
            })
    return cleaned

# Read Khush's transcript.json
with open("output/transcript.json", "r") as f:
    segments = json.load(f)

# Clean and label
cleaned_segments = clean_transcript(segments)

# Build output
output = {
    "total_segments": len(cleaned_segments),
    "segments": cleaned_segments
}

# Save
with open("output/cleaned_transcript.json", "w") as f:
    json.dump(output, f, indent=4)

print("Saved cleaned_transcript.json\n")

# Pretty print to console
for seg in cleaned_segments:
    print(f"[{seg['speaker']}] ({seg['start']}s - {seg['end']}s)")
    print(f"  {seg['text']}\n")