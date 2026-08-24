import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.classifier import (
    CATEGORY_BINARY,
    CATEGORY_CODE,
    CATEGORY_CONFIG,
    CATEGORY_IMAGE,
    CATEGORY_TEXT,
    CATEGORY_UNKNOWN,
    classify_file,
    is_probably_binary,
    match_sensitive,
)


def test_python_file_classified_as_code():
    result = classify_file("src/main.py")
    assert result.category == CATEGORY_CODE
    assert result.language == "python"
    assert result.is_binary is False


def test_json_classified_as_config():
    result = classify_file("config/settings.json")
    assert result.category == CATEGORY_CONFIG


def test_markdown_classified_as_text():
    result = classify_file("README.md")
    assert result.category == CATEGORY_TEXT


def test_image_classified_as_image_and_binary():
    result = classify_file("assets/logo.png")
    assert result.category == CATEGORY_IMAGE
    assert result.is_binary is True


def test_unknown_extension_without_sample_is_unknown():
    result = classify_file("mystery.qzx")
    assert result.category == CATEGORY_UNKNOWN


def test_unknown_extension_with_binary_sample_is_binary():
    sample = bytes([0, 1, 2, 3, 255, 254]) * 10
    result = classify_file("mystery.qzx", read_sample=sample)
    assert result.category == CATEGORY_BINARY


def test_env_file_flagged_sensitive():
    result = classify_file(".env")
    assert result.is_sensitive is True


def test_pem_key_flagged_sensitive():
    result = classify_file("server.pem")
    assert result.is_sensitive is True
    assert match_sensitive("private.key") == "*.key"


def test_normal_python_file_not_sensitive():
    result = classify_file("main.py")
    assert result.is_sensitive is False


def test_is_probably_binary_detects_null_byte():
    assert is_probably_binary(b"hello\x00world") is True


def test_is_probably_binary_false_for_plain_text():
    assert is_probably_binary("Hej, det här är vanlig text.".encode("utf-8")) is False
