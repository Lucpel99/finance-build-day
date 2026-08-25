from __future__ import annotations

import re

_PUNCT = re.compile(r"[-./#_]+")
_WS = re.compile(r"\s+")
_DIGITS = re.compile(r"\d+")

MIN_SUBSTRING = 4
MIN_OCR_DIGITS = 6


def normalize(text: str | None) -> str:
    if not text:
        return ""
    folded = str(text).upper().replace("\u00a0", " ")
    folded = _PUNCT.sub(" ", folded)
    folded = _WS.sub(" ", folded).strip()
    return folded


def digits_only(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\D", "", str(text))


def digit_runs(text: str | None) -> list[str]:
    if not text:
        return []
    return _DIGITS.findall(str(text))


def build_needles(*raw: str | None) -> list[str]:
    needles: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        if value and value not in seen:
            seen.add(value)
            needles.append(value)

    for item in raw:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        folded = normalize(text)
        if len(folded.replace(" ", "")) >= MIN_SUBSTRING:
            add(folded)
        digits = digits_only(text)
        if len(digits) >= MIN_OCR_DIGITS:
            add(digits)
    return needles


def needles_match_haystack(needles: list[str], haystack: str | None) -> bool:
    hay = normalize(haystack)
    if not hay or not needles:
        return False
    hay_compact = hay.replace(" ", "")
    hay_all_digits = digits_only(haystack)
    hay_digits = set(run for run in digit_runs(haystack) if len(run) >= MIN_OCR_DIGITS)
    hay_tokens = set(hay.split())

    for needle in needles:
        folded = normalize(needle)
        if not folded:
            continue
        compact = folded.replace(" ", "")
        if len(compact) >= MIN_SUBSTRING and compact in hay_compact:
            return True
        if folded in hay_tokens:
            return True
        digits = digits_only(needle)
        if len(digits) >= MIN_OCR_DIGITS and (
            digits in hay_digits or digits in hay_all_digits
        ):
            return True
    return False
