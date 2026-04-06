import json
import os
import shutil
import time
from pathlib import Path


def _ensure_ffmpeg_on_path() -> None:
    """Whisper shells out to the command ``ffmpeg``; bundle a real binary as ffmpeg.exe if needed."""
    _log_p = Path(__file__).resolve().parent.parent.parent / "debug-7d999b.log"

    def _ensure_log(msg: str, data: dict) -> None:
        # #region agent log
        try:
            with open(_log_p, "a", encoding="utf-8") as lf:
                lf.write(
                    json.dumps(
                        {
                            "sessionId": "7d999b",
                            "timestamp": int(time.time() * 1000),
                            "location": "transcribe.py:_ensure_ffmpeg_on_path",
                            "message": msg,
                            "data": data,
                            "hypothesisId": "H1-shim",
                        },
                        default=str,
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

    if shutil.which("ffmpeg"):
        _ensure_log("skip_ensure", {"which": shutil.which("ffmpeg")})
        return
    try:
        import imageio_ffmpeg

        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
        if bundled.name.lower() == "ffmpeg.exe":
            os.environ["PATH"] = str(bundled.parent) + os.pathsep + os.environ.get("PATH", "")
            _ensure_log(
                "path_prepended",
                {"bundled": str(bundled), "which_after": shutil.which("ffmpeg")},
            )
            return

        shim_dir = Path(__file__).resolve().parent / ".ffmpeg_shim"
        shim_dir.mkdir(parents=True, exist_ok=True)
        shim = shim_dir / "ffmpeg.exe"
        needs_copy = not shim.is_file()
        if shim.is_file() and bundled.is_file():
            s_st, b_st = shim.stat(), bundled.stat()
            needs_copy = needs_copy or s_st.st_size != b_st.st_size
        if needs_copy:
            shutil.copy2(bundled, shim)
        os.environ["PATH"] = str(shim_dir) + os.pathsep + os.environ.get("PATH", "")
        _ensure_log(
            "shim_ready",
            {
                "bundled": str(bundled),
                "bundled_name": bundled.name,
                "shim": str(shim),
                "which_after": shutil.which("ffmpeg"),
            },
        )
    except Exception as e:
        _ensure_log(
            "ensure_failed",
            {"type": type(e).__name__, "detail": str(e)},
        )


_ensure_ffmpeg_on_path()

import whisper  # noqa: E402

_model = None

_DEBUG_LOG = Path(__file__).resolve().parent.parent.parent / "debug-7d999b.log"


def _agent_log(location: str, message: str, data: dict, hypothesis_id: str) -> None:
    # #region agent log
    try:
        entry = {
            "sessionId": "7d999b",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        }
        with open(_DEBUG_LOG, "a", encoding="utf-8") as lf:
            lf.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass
    # #endregion


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def transcribe_audio(audio_path):
    p = Path(audio_path)
    # #region agent log
    _agent_log(
        "transcribe.py:transcribe_audio",
        "entry",
        {
            "audio_path": str(p),
            "exists": p.is_file(),
            "size": p.stat().st_size if p.is_file() else None,
        },
        "H2",
    )
    # #endregion

    model = _get_model()
    # #region agent log
    _agent_log(
        "transcribe.py:transcribe_audio",
        "before model.transcribe",
        {},
        "H1-H4",
    )
    # #endregion

    try:
        result = model.transcribe(audio_path)
    except Exception as e:
        # #region agent log
        _agent_log(
            "transcribe.py:transcribe_audio",
            "transcribe raised",
            {"type": type(e).__name__, "detail": str(e)},
            "H1-H4",
        )
        # #endregion
        raise

    # #region agent log
    _agent_log(
        "transcribe.py:transcribe_audio",
        "after model.transcribe",
        {"text_len": len((result or {}).get("text") or "")},
        "H1",
    )
    # #endregion

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
