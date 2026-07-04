"""Tests for multimodal vision prompt builder."""
from app.vision import (
    affection_tier_label,
    build_vision_system_prompt,
    clamp_affection,
    decode_base64_image,
)


def test_clamp_affection():
    assert clamp_affection(150) == 100
    assert clamp_affection(-5) == 0
    assert clamp_affection("42") == 42


def test_affection_tier():
    assert affection_tier_label(30) == "low"
    assert affection_tier_label(80) == "high"


def test_build_vision_prompt_shiro_high():
    prompt = build_vision_system_prompt("shiro", 75)
    assert "Shiro" in prompt
    assert "51" in prompt or "clingy" in prompt.lower() or "dekat" in prompt.lower()
    assert "teks_layar" in prompt


def test_build_vision_prompt_sishin_low():
    prompt = build_vision_system_prompt("sishin", 25)
    assert "Sishin" in prompt
    assert "elegan" in prompt.lower() or "refined" in prompt.lower() or "anggun" in prompt.lower()


def test_decode_base64_image():
    # 1x1 red pixel PNG
    b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQ"
        "AAAABJRU5ErkJggg=="
    )
    data, mime = decode_base64_image(b64)
    assert len(data) > 0
    assert mime == "image/jpeg" or mime.startswith("image/")
