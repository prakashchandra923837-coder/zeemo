"""
zeemo_core.py — Lightweight Mobile Engine for Zeemo Clone APK
Works on Android (Kivy + Buildozer) using only Python stdlib + requests.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CaptionStyle:
    name: str
    font_name: str
    font_size: int
    primary_color: str
    highlight_color: str
    outline_color: str
    back_color: str
    outline_width: int
    shadow_depth: int
    bold: bool
    uppercase: bool
    box_style: int
    pop_animation: bool


STYLE_PRESETS: Dict[str, CaptionStyle] = {
    "zeemo_pop": CaptionStyle(
        name="Zeemo Pop (Bold + Yellow)",
        font_name="Roboto",
        font_size=64,
        primary_color="#FFFFFF",
        highlight_color="#FFD700",
        outline_color="#000000",
        back_color="#000000",
        outline_width=5,
        shadow_depth=2,
        bold=True,
        uppercase=True,
        box_style=1,
        pop_animation=True,
    ),
    "hormozi_green": CaptionStyle(
        name="Hormozi Green",
        font_name="Roboto",
        font_size=68,
        primary_color="#FFFFFF",
        highlight_color="#00FF7F",
        outline_color="#000000",
        back_color="#000000",
        outline_width=6,
        shadow_depth=3,
        bold=True,
        uppercase=True,
        box_style=1,
        pop_animation=True,
    ),
    "mrbeast_bold": CaptionStyle(
        name="MrBeast Red Pop",
        font_name="Roboto",
        font_size=70,
        primary_color="#FFFFFF",
        highlight_color="#FF3B30",
        outline_color="#000000",
        back_color="#000000",
        outline_width=7,
        shadow_depth=4,
        bold=True,
        uppercase=True,
        box_style=1,
        pop_animation=True,
    ),
    "neon_karaoke": CaptionStyle(
        name="Neon Cyan Karaoke",
        font_name="Roboto",
        font_size=60,
        primary_color="#E0F7FA",
        highlight_color="#00E5FF",
        outline_color="#0D1B2A",
        back_color="#000000",
        outline_width=4,
        shadow_depth=3,
        bold=True,
        uppercase=False,
        box_style=1,
        pop_animation=True,
    ),
    "minimal_box": CaptionStyle(
        name="Minimal Dark Box",
        font_name="Roboto",
        font_size=50,
        primary_color="#FFFFFF",
        highlight_color="#FFE066",
        outline_color="#141414",
        back_color="#141414",
        outline_width=10,
        shadow_depth=0,
        bold=True,
        uppercase=False,
        box_style=3,
        pop_animation=False,
    ),
}

EMOJI_MAP: Dict[str, str] = {
    "money": "💰", "cash": "💵", "paisa": "💰", "paise": "💰", "पैसा": "💰",
    "fire": "🔥", "viral": "🔥", "aag": "🔥", "idea": "💡", "secret": "🤫",
    "fast": "⚡", "jaldi": "⚡", "grow": "📈", "views": "👀", "love": "❤️",
    "pyar": "❤️", "happy": "😊", "funny": "😂", "goal": "🎯", "win": "🏆",
    "rocket": "🚀", "ai": "🤖", "video": "🎬", "stop": "🛑", "time": "⏰",
    "check": "✅", "free": "🆓", "music": "🎵", "phone": "📱",
}


def hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        hex_color = "FFFFFF"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H{alpha:02X}{b.upper()}{g.upper()}{r.upper()}"


def format_srt_time(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    hrs, ms = divmod(ms, 3600000)
    mins, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def format_ass_time(seconds: float) -> str:
    cs = int(round(max(0.0, seconds) * 100))
    hrs, cs = divmod(cs, 360000)
    mins, cs = divmod(cs, 6000)
    secs, cs = divmod(cs, 100)
    return f"{hrs:d}:{mins:02d}:{secs:02d}.{cs:02d}"


def transcribe_via_api(
    media_path: str,
    api_key: str,
    provider: str = "groq",
    language: str = "auto",
) -> Tuple[List[dict], str]:
    """Call Groq or OpenAI Whisper API to get word-level timestamps."""
    import requests

    if not api_key.strip():
        raise ValueError("API key is required for mobile cloud transcription.")

    if provider == "groq":
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        model = "whisper-large-v3-turbo"
    else:
        url = "https://api.openai.com/v1/audio/transcriptions"
        model = "whisper-1"

    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    data: List[Tuple[str, str]] = [
        ("model", model),
        ("response_format", "verbose_json"),
        ("timestamp_granularities[]", "word"),
        ("timestamp_granularities[]", "segment"),
    ]
    if language and language != "auto":
        data.append(("language", language))

    with open(media_path, "rb") as f:
        files = {"file": (os.path.basename(media_path), f, "application/octet-stream")}
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=180)

    if resp.status_code != 200:
        raise RuntimeError(f"API Error {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    words: List[dict] = []
    if payload.get("words"):
        for w in payload["words"]:
            tok = (w.get("word") or "").strip()
            if tok:
                words.append({"word": tok, "start": float(w["start"]), "end": float(w["end"])})
    elif payload.get("segments"):
        # Fallback: split segments evenly if API returned segment-level only
        for seg in payload["segments"]:
            tokens = (seg.get("text") or "").strip().split()
            if not tokens:
                continue
            s_t, e_t = float(seg["start"]), float(seg["end"])
            step = max(0.1, (e_t - s_t) / len(tokens))
            for i, tok in enumerate(tokens):
                words.append({"word": tok, "start": s_t + i * step, "end": s_t + (i + 1) * step})

    return words, payload.get("language", language)


def group_words_into_chunks(
    words: List[dict],
    max_words_per_line: int = 3,
    max_gap_sec: float = 0.55,
) -> List[Dict[str, Any]]:
    if not words:
        return []
    chunks: List[Dict[str, Any]] = []
    current: List[dict] = []

    for w in words:
        if current:
            gap = w["start"] - current[-1]["end"]
            ends_sentence = current[-1]["word"][-1] in ".!?।,"
            if len(current) >= max_words_per_line or gap > max_gap_sec or ends_sentence:
                chunks.append({
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "text": " ".join(x["word"] for x in current),
                    "words": current,
                })
                current = []
        current.append(w)

    if current:
        chunks.append({
            "start": current[0]["start"],
            "end": current[-1]["end"],
            "text": " ".join(x["word"] for x in current),
            "words": current,
        })
    return chunks


def add_auto_emojis(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for chunk in chunks:
        tokens = re.findall(r"[\w\u0900-\u097F]+", chunk["text"].lower())
        emoji = next((EMOJI_MAP[t] for t in tokens if t in EMOJI_MAP), "")
        if emoji and emoji not in chunk["text"]:
            chunk["text"] = f"{chunk['text']} {emoji}"
            if chunk.get("words"):
                chunk["words"][-1]["word"] = f"{chunk['words'][-1]['word']} {emoji}"
    return chunks


def chunks_to_editor_text(chunks: List[Dict[str, Any]]) -> str:
    lines = []
    for i, c in enumerate(chunks, start=1):
        lines.append(f"{i} | {format_srt_time(c['start'])} --> {format_srt_time(c['end'])} | {c['text']}")
    return "\n".join(lines)


def write_srt(chunks: List[Dict[str, Any]], srt_path: str, uppercase: bool = False) -> None:
    lines = []
    for i, c in enumerate(chunks, start=1):
        txt = c["text"].upper() if uppercase else c["text"]
        lines.append(f"{i}\n{format_srt_time(c['start'])} --> {format_srt_time(c['end'])}\n{txt}\n")
    Path(srt_path).write_text("\n".join(lines), encoding="utf-8")


def write_ass(
    chunks: List[Dict[str, Any]],
    ass_path: str,
    style: CaptionStyle,
    video_size: Tuple[int, int] = (1080, 1920),
    position: str = "Bottom",
) -> None:
    width, height = video_size
    align_map = {"Bottom": (2, 160), "Center": (5, 0), "Top": (8, 160)}
    alignment, margin_v = align_map.get(position, (2, 160))

    prim_ass = hex_to_ass_color(style.primary_color)
    high_ass = hex_to_ass_color(style.highlight_color)
    outl_ass = hex_to_ass_color(style.outline_color)
    back_ass = hex_to_ass_color(style.back_color, alpha=110 if style.box_style == 3 else 128)
    bold_flag = -1 if style.bold else 0

    header = f"""[Script Info]
Title: Zeemo Mobile Captions
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{prim_ass},{high_ass},{outl_ass},{back_ass},{bold_flag},0,0,0,100,100,0,0,{style.box_style},{style.outline_width},{style.shadow_depth},{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    pop_tag = r"{\fscx85\fscy85\t(0,80,\fscx106\fscy106)\t(80,150,\fscx100\fscy100)}" if style.pop_animation else ""

    for chunk in chunks:
        words = chunk.get("words") or []
        chunk_end = chunk["end"]
        for active_idx, active_word in enumerate(words):
            w_start = active_word["start"]
            w_end = words[active_idx + 1]["start"] if active_idx + 1 < len(words) else chunk_end
            if w_end <= w_start:
                w_end = w_start + 0.08
            parts = []
            for j, w in enumerate(words):
                tok = w["word"].upper() if style.uppercase else w["word"]
                tok = tok.replace("{", "(").replace("}", ")")
                parts.append(f"{{\\c{high_ass}}}{tok}{{\\c{prim_ass}}}" if j == active_idx else tok)
            line = (pop_tag if active_idx == 0 else "") + " ".join(parts)
            events.append(f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{line}")

    Path(ass_path).write_text(header + "\n".join(events) + "\n", encoding="utf-8")
