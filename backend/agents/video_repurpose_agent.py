import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid

from google import genai
from google.genai import types

from backend.config import GEMINI_MODEL, GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Platform aspect-ratio configurations
_PLATFORM_CONFIGS: dict[str, dict] = {
    "reels": {"width": 1080, "height": 1920},
    "tiktok": {"width": 1080, "height": 1920},
    "youtube_shorts": {"width": 1080, "height": 1920},
    "linkedin": {"width": 1080, "height": 1080},
}


# ── FFmpeg helpers ─────────────────────────────────────────────────────────────

def _run_ffmpeg(args: list[str]) -> None:
    """Run an FFmpeg command; raises RuntimeError on non-zero exit."""
    cmd = ["ffmpeg", "-y"] + args
    logger.debug("FFmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg stderr: %s", result.stderr[-2000:])
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-400:]}")


def _extract_clip(input_path: str, output_path: str, start: float, end: float) -> None:
    _run_ffmpeg([
        "-i", input_path,
        "-ss", str(start), "-to", str(end),
        "-c:v", "libx264", "-c:a", "aac",
        output_path,
    ])


def _format_for_platform(input_path: str, output_path: str, platform: str) -> None:
    cfg = _PLATFORM_CONFIGS.get(platform, _PLATFORM_CONFIGS["reels"])
    w, h = cfg["width"], cfg["height"]
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
    )
    _run_ffmpeg(["-i", input_path, "-vf", vf, "-c:a", "copy", output_path])


# ── Gemini video analysis ──────────────────────────────────────────────────────

async def _upload_to_gemini_files(video_path: str) -> object:
    """Upload a video file to the Gemini Files API and wait until ACTIVE."""
    client = genai.Client(api_key=GOOGLE_API_KEY)

    video_file = await asyncio.to_thread(
        client.files.upload,
        path=video_path,
        config={"mime_type": "video/mp4"},
    )

    # Poll until Gemini finishes processing the video
    while getattr(video_file.state, "name", str(video_file.state)) == "PROCESSING":
        await asyncio.sleep(4)
        video_file = await asyncio.to_thread(client.files.get, name=video_file.name)

    state_name = getattr(video_file.state, "name", str(video_file.state))
    if state_name != "ACTIVE":
        raise ValueError(f"Gemini file processing failed (state={state_name})")

    return video_file, client


async def _analyze_video(video_file: object, client: object, brand_profile: dict) -> list[dict]:
    """Ask Gemini to identify the top 3 clip-worthy moments in the video."""
    business = brand_profile.get("business_name") or brand_profile.get("name", "this brand")
    tone = brand_profile.get("tone", "professional")
    industry = brand_profile.get("industry", "business")
    caption_hint = brand_profile.get("caption_style_directive", "")

    caption_note = f" Write captions in this style: {caption_hint[:120]}" if caption_hint else ""

    prompt = f"""Analyze this video for a {industry} brand called "{business}" (tone: {tone}).

Identify the TOP 3 most clip-worthy moments for social media short-form content.

For each clip, choose the most suitable platform:
- "reels" or "tiktok": 15–60 seconds, hook in first 3 seconds, high energy
- "linkedin": 30–90 seconds, insight-driven, professional
- "youtube_shorts": 15–60 seconds, fast-paced

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "start_time": 12.5,
    "end_time": 42.0,
    "platform": "reels",
    "hook": "The verbatim opening line or moment that immediately grabs attention",
    "suggested_caption": "A ready-to-post caption in the brand voice.{caption_note}",
    "reason": "One sentence on why this moment is compelling"
  }}
]

Rules:
- Timestamps must be in seconds (floats), accurate to the video content.
- Do NOT overlap clips.
- Sort by engagement potential (best first).
- Each clip MUST have a strong opening hook."""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=GEMINI_MODEL,
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        specs = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned unparseable JSON: {e}") from e

    if not isinstance(specs, list) or len(specs) == 0:
        raise ValueError("Gemini found no clip-worthy moments in this video")

    return specs


# ── Public API ─────────────────────────────────────────────────────────────────

async def analyze_and_repurpose(video_bytes: bytes, brand_profile: dict) -> list[dict]:
    """
    Analyze a raw video using Gemini and extract up to 3 platform-ready short clips.

    Args:
        video_bytes: Raw MP4/MOV video bytes.
        brand_profile: Brand Firestore document (needs business_name, tone, industry, etc.)

    Returns:
        List of clip dicts, each with keys:
          platform, start_time, end_time, duration_seconds,
          hook, suggested_caption, reason, clip_bytes, filename

    Raises:
        ValueError: Gemini analysis failed or no clips found.
        RuntimeError: FFmpeg not installed or processing failed.
    """
    tmpdir = tempfile.mkdtemp(prefix="vrepurpose_")
    try:
        # 1 ─ Write source video to disk
        source_path = os.path.join(tmpdir, f"source_{uuid.uuid4().hex[:8]}.mp4")
        with open(source_path, "wb") as f:
            f.write(video_bytes)

        # 2 ─ Upload to Gemini Files API
        logger.info("Uploading %d-byte video to Gemini Files API…", len(video_bytes))
        video_file, client = await _upload_to_gemini_files(source_path)
        logger.info("Gemini file ready: %s", video_file.name)

        # 3 ─ Analyze for clip-worthy moments
        clip_specs = await _analyze_video(video_file, client, brand_profile)
        logger.info("Gemini identified %d clips", len(clip_specs))

        # Delete from Gemini Files API (non-blocking cleanup)
        asyncio.create_task(
            asyncio.to_thread(client.files.delete, name=video_file.name)
        )

        # 4 ─ Extract and format each clip with FFmpeg
        clips = []
        for i, spec in enumerate(clip_specs[:3]):
            start = float(spec.get("start_time", 0))
            end = float(spec.get("end_time", start + 30))
            platform = spec.get("platform", "reels")
            clip_tag = f"clip_{i + 1}_{platform}"

            raw_path = os.path.join(tmpdir, f"{clip_tag}_raw.mp4")
            final_path = os.path.join(tmpdir, f"{clip_tag}_final.mp4")

            logger.info("Extracting clip %d: %.1f–%.1f → %s", i + 1, start, end, platform)
            await asyncio.to_thread(_extract_clip, source_path, raw_path, start, end)
            await asyncio.to_thread(_format_for_platform, raw_path, final_path, platform)

            with open(final_path, "rb") as f:
                clip_bytes = f.read()

            clips.append({
                "platform": platform,
                "start_time": start,
                "end_time": end,
                "duration_seconds": round(end - start, 1),
                "hook": spec.get("hook", ""),
                "suggested_caption": spec.get("suggested_caption", ""),
                "reason": spec.get("reason", ""),
                "clip_bytes": clip_bytes,
                "filename": f"{clip_tag}.mp4",
            })

        return clips

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
