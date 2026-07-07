"""
Video processing for Shiro AI — keyframe extraction for Gemini Vision.

Uses ffmpeg/ffprobe when available (recommended). Falls back to OpenCV if installed.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import List, Tuple

from app import config

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
VIDEO_MIMES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-m4v",
    "video/x-msvideo",
}

_EXT_BY_MIME = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-m4v": ".m4v",
}


def guess_video_suffix(mime_type: str, filename: str = "") -> str:
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime in _EXT_BY_MIME:
        return _EXT_BY_MIME[mime]
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            return ext
    return ".mp4"


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _probe_duration(video_path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return max(0.5, float(result.stdout.strip()))
    except Exception as exc:
        logger.debug("ffprobe duration failed: %s", exc)
    return 5.0


def _extract_with_ffmpeg(video_path: str, max_frames: int) -> List[Tuple[bytes, str]]:
    frames: List[Tuple[bytes, str]] = []
    duration = _probe_duration(video_path)

    with tempfile.TemporaryDirectory() as tmp:
        for i in range(max_frames):
            ts = max(0.05, duration * (i + 1) / (max_frames + 1))
            out_path = os.path.join(tmp, f"frame_{i:02d}.jpg")
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        f"{ts:.3f}",
                        "-i",
                        video_path,
                        "-vframes",
                        "1",
                        "-q:v",
                        "2",
                        out_path,
                    ],
                    capture_output=True,
                    timeout=60,
                    check=False,
                )
                if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
                    with open(out_path, "rb") as fh:
                        frames.append((fh.read(), "image/jpeg"))
            except Exception as exc:
                logger.debug("ffmpeg frame %s failed: %s", i, exc)
    return frames


def _extract_with_opencv(video_path: str, max_frames: int) -> List[Tuple[bytes, str]]:
    try:
        import cv2  # type: ignore
    except ImportError:
        return []

    frames: List[Tuple[bytes, str]] = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return frames

    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            total = max_frames * 10

        indices = [
            max(0, int(total * (i + 1) / (max_frames + 1)))
            for i in range(max_frames)
        ]

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if ok:
                frames.append((buf.tobytes(), "image/jpeg"))
    finally:
        cap.release()

    return frames


def extract_keyframes_from_bytes(
    video_bytes: bytes,
    mime_type: str = "video/mp4",
    filename: str = "",
    max_frames: int | None = None,
) -> List[Tuple[bytes, str]]:
    """
    Extract representative JPEG keyframes from video bytes.
    Returns list of (jpeg_bytes, mime_type).
    """
    if not video_bytes:
        return []

    max_frames = max_frames or getattr(config, "VIDEO_KEYFRAME_COUNT", 4)
    max_frames = max(1, min(int(max_frames), 6))
    suffix = guess_video_suffix(mime_type, filename)

    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, f"clip{suffix}")
        with open(video_path, "wb") as fh:
            fh.write(video_bytes)

        frames: List[Tuple[bytes, str]] = []
        if _ffmpeg_available():
            frames = _extract_with_ffmpeg(video_path, max_frames)
        if not frames:
            frames = _extract_with_opencv(video_path, max_frames)

        return frames


def save_uploaded_video(video_bytes: bytes, mime_type: str, filename: str = "") -> str:
    """Persist video under static/uploads/videos/. Returns public URL path."""
    import uuid

    upload_dir = getattr(config, "VIDEO_UPLOAD_DIR", None)
    if not upload_dir:
        upload_dir = os.path.join(config.BASE_DIR, "static", "uploads", "videos")
    os.makedirs(upload_dir, exist_ok=True)

    suffix = guess_video_suffix(mime_type, filename)
    name = f"{uuid.uuid4().hex}{suffix}"
    path = os.path.join(upload_dir, name)
    with open(path, "wb") as fh:
        fh.write(video_bytes)
    return f"/static/uploads/videos/{name}"
