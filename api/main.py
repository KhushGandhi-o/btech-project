import importlib.util
import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
_DEBUG_LOG = ROOT / "debug-7d999b.log"


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


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from entity_extraction.entity_extraction import extract_with_biobert
from modules.speech_to_text.transcribe import transcribe_audio

AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".mpeg",
    ".mp4",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".webm",
    ".wma",
    ".aiff",
    ".aif",
    ".caf",
    ".alac",
}

_clean_mod = None


def _get_clean_module():
    global _clean_mod
    if _clean_mod is None:
        path = ROOT / "transcript cleaning" / "clean_transcript.py"
        spec = importlib.util.spec_from_file_location("clean_transcript_mod", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load transcript cleaning module")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _clean_mod = mod
    return _clean_mod


def _format_cleaned_dialogue(cleaned: dict) -> str:
    lines = []
    for seg in cleaned.get("segments", []):
        sp = seg.get("speaker", "Unknown")
        lines.append(f"[{sp}] {seg.get('text', '')}")
    return "\n".join(lines)


def _format_soap_note(soap: dict) -> str:
    parts = []
    for key in ("Subjective", "Objective", "Assessment", "Plan"):
        items = soap.get(key) or []
        parts.append(f"{key.upper()}")
        if items:
            for item in items:
                parts.append(f"  • {item}")
        else:
            parts.append("  • (none extracted)")
        parts.append("")
    return "\n".join(parts).rstrip()


app = FastAPI(title="Clinical Audio → Transcript & SOAP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/process-audio")
async def process_audio(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if not suffix:
        raise HTTPException(
            status_code=400,
            detail="File has no extension; please use a recognizable audio file.",
        )
    if suffix not in AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio extension '{suffix}'. Allowed: {', '.join(sorted(AUDIO_EXTENSIONS))}",
        )

    body = await file.read()
    if not body:
        raise HTTPException(status_code=400, detail="Empty file")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(body)
            tmp_path = Path(tmp.name)

        # #region agent log
        _agent_log(
            "api/main.py:process_audio",
            "temp file written",
            {
                "tmp_path": str(tmp_path),
                "exists": tmp_path.is_file(),
                "size": tmp_path.stat().st_size if tmp_path.is_file() else None,
                "ffmpeg_which": shutil.which("ffmpeg"),
                "ffprobe_which": shutil.which("ffprobe"),
                "runId": "post-fix",
            },
            "H1-H2",
        )
        # #endregion

        # #region agent log
        _agent_log(
            "api/main.py:process_audio",
            "calling transcribe_audio",
            {"path": str(tmp_path)},
            "H2-H4",
        )
        # #endregion

        transcript_text, raw_segments = transcribe_audio(str(tmp_path))

        # #region agent log
        _agent_log(
            "api/main.py:process_audio",
            "transcribe OK, starting clean+soap",
            {"raw_seg_count": len(raw_segments) if raw_segments else 0},
            "H3",
        )
        # #endregion

        clean = _get_clean_module().build_cleaned_transcript(raw_segments)
        soap = extract_with_biobert(clean["segments"])

        return {
            "filename": file.filename,
            "transcript": transcript_text.strip(),
            "cleaned_dialogue": _format_cleaned_dialogue(clean),
            "cleaned_transcript": clean,
            "soap": soap,
            "soap_note": _format_soap_note(soap),
        }
    except HTTPException:
        raise
    except Exception as e:
        # #region agent log
        _agent_log(
            "api/main.py:process_audio",
            "exception",
            {
                "type": type(e).__name__,
                "detail": str(e),
                "traceback": traceback.format_exc(),
            },
            "H1-H5",
        )
        # #endregion
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


app.mount(
    "/",
    StaticFiles(directory=str(ROOT / "web"), html=True),
    name="web",
)
