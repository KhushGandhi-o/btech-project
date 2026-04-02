import whisper
import json

model = whisper.load_model("base")

def transcribe_audio(audio_path):

    result = model.transcribe(audio_path)

    transcript = result["text"]
    segments = result["segments"]

    structured_output = []

    for seg in segments:
        structured_output.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"]
        })

    return transcript, structured_output


def save_transcript(data, output_path):

    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":

    audio_file = "audio/test1.wav"

    transcript, segments = transcribe_audio(audio_file)

    print("\nFull Transcript:\n")
    print(transcript)

    save_transcript(segments, "output/transcript.json")

    print("\nSaved transcript with timestamps.")
