"""Tests for video keyframe helpers."""
from app.video import guess_video_suffix, VIDEO_EXTENSIONS


def test_guess_video_suffix_from_mime():
    assert guess_video_suffix("video/webm") == ".webm"
    assert guess_video_suffix("video/quicktime") == ".mov"
    assert guess_video_suffix("video/mp4", "clip.MP4") == ".mp4"


def test_guess_video_suffix_from_filename():
    assert guess_video_suffix("", "movie.mov") == ".mov"


def test_video_extensions_set():
    assert ".mp4" in VIDEO_EXTENSIONS
    assert ".webm" in VIDEO_EXTENSIONS
