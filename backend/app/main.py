import os, io, base64, tempfile
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import soundfile as sf
from moviepy.editor import ImageClip, AudioFileClip

from .utils import (
    data_uri_to_bytes,
    caption_image,
    combine_side_by_side,
    now_slug,
    # ⬇️ add these three:
    auto_caption_canvas,
    extract_context_objects,
    layout_with_context_panel,
)
from .ai import suggest_captions, generate_image


load_dotenv()
API_TITLE = "MemeForge Studio Backend"
API_VERSION = "2.0.0"

app = FastAPI(title=API_TITLE, version=API_VERSION)

origins = os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_PATH = os.getenv("IMPACT_PATH", None)
if FONT_PATH and not os.path.isabs(FONT_PATH):
    FONT_PATH = os.path.join(os.path.dirname(__file__), "..", FONT_PATH)

# ------------ Existing schemas ------------
class QuickMemeIn(BaseModel):
    imageDataUri: Optional[str] = None
    topText: Optional[str] = ""
    bottomText: Optional[str] = ""
    width: int = 1080
    height: int = 1080

class RemixIn(BaseModel):
    leftDataUri: str
    rightDataUri: str
    vertical: bool = False

class KaraokeIn(BaseModel):
    imageDataUri: str
    caption: str
    durationSec: float = 6.0
    audioDataUri: Optional[str] = None  # prefer WAV data URI

# ------------ NEW AI schemas ------------
class CaptionSuggestIn(BaseModel):
    topic: str
    n: int = 5

class MemeGenIn(BaseModel):
    prompt: str
    negative: Optional[str] = ""
    styleTop: Optional[str] = ""      # e.g., shouty, sarcastic
    styleBottom: Optional[str] = ""
    seed: Optional[int] = None
    width: int = 1080
    height: int = 1080

@app.get("/health")
def health():
    return {"status": "ok", "service": API_TITLE, "version": API_VERSION}

# ---------- Classic endpoints ----------
@app.post("/quick_meme")
def quick_meme(inp: QuickMemeIn):
    if inp.imageDataUri:
        img = Image.open(io.BytesIO(data_uri_to_bytes(inp.imageDataUri))).convert("RGB")
        img = img.resize((inp.width, inp.height), Image.LANCZOS)
    else:
        img = Image.new("RGB", (inp.width, inp.height), color=(32, 32, 32))
    img = caption_image(img, inp.topText or "", inp.bottomText or "", FONT_PATH)
    out_name = f"meme_{now_slug()}.png"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    img.save(out_path, "PNG")
    return {"file": out_name, "download": f"/download/{out_name}"}

@app.post("/remix")
def remix(inp: RemixIn):
    l = Image.open(io.BytesIO(data_uri_to_bytes(inp.leftDataUri))).convert("RGB")
    r = Image.open(io.BytesIO(data_uri_to_bytes(inp.rightDataUri))).convert("RGB")
    if not inp.vertical:
        target_h = min(l.height, r.height)
        l = l.resize((int(l.width * target_h / l.height), target_h), Image.LANCZOS)
        r = r.resize((int(r.width * target_h / r.height), target_h), Image.LANCZOS)
    else:
        target_w = min(l.width, r.width)
        l = l.resize((target_w, int(l.height * target_w / l.width)), Image.LANCZOS)
        r = r.resize((target_w, int(r.height * target_w / r.width)), Image.LANCZOS)
    combined = combine_side_by_side(l, r, vertical=inp.vertical)
    out_name = f"remix_{now_slug()}.png"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    combined.save(out_path, "PNG")
    return {"file": out_name, "download": f"/download/{out_name}"}

@app.get("/download/{name}")
def download(name: str):
    fp = os.path.join(OUTPUT_DIR, name)
    if not os.path.exists(fp):
        raise HTTPException(404, "File not found")
    with open(fp, "rb") as f:
        b = f.read()
    mime = "image/png" if name.lower().endswith(".png") else "video/mp4"
    return {"name": name, "dataUri": "data:%s;base64,%s" % (mime, base64.b64encode(b).decode("ascii"))}

def make_tone(duration: float, sr: int = 16000, freq: float = 440.0):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False).astype(np.float32)
    x = 0.1 * np.sin(2 * np.pi * freq * t).astype(np.float32)
    return x, sr

@app.post("/karaoke")
def karaoke(inp: KaraokeIn):
    img = Image.open(io.BytesIO(data_uri_to_bytes(inp.imageDataUri))).convert("RGB").resize((1080,1080))
    frame_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    base = img.copy()
    draw = ImageDraw.Draw(base)
    font_size = 60
    try:
        font = ImageFont.truetype(FONT_PATH if FONT_PATH else "arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    words = inp.caption.split()
    lines, cur = [], ""
    W,H = base.size
    maxw = int(W*0.9)
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= maxw:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    total_h = int(len(lines)*(font_size*1.2))
    y = H - total_h - 40
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (W - w)//2
        draw.text((x, y), line, fill=(0,0,0), font=font, stroke_width=4, stroke_fill=(0,0,0))
        draw.text((x, y), line, fill=(255,255,255), font=font)
        y += int(font_size*1.2)
    base.save(frame_tmp.name, "PNG")
    if inp.audioDataUri:
        ab = data_uri_to_bytes(inp.audioDataUri)
        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with open(tmp_wav.name, "wb") as f:
            f.write(ab)
        audio_path = tmp_wav.name
    else:
        x, sr = make_tone(inp.durationSec)
        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        sf.write(tmp_wav.name, x, sr, format="WAV", subtype="PCM_16")
        audio_path = tmp_wav.name
    clip = ImageClip(frame_tmp.name).set_duration(inp.durationSec)
    try:
        aclip = AudioFileClip(audio_path).set_duration(inp.durationSec)
        clip = clip.set_audio(aclip)
    except Exception:
        pass
    out_name = f"karaoke_{now_slug()}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    clip.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
    return {"file": out_name, "download": f"/download/{out_name}"}

# ---------- NEW: AI endpoints ----------
@app.post("/suggest_captions")
def api_suggest_captions(inp: CaptionSuggestIn):
    return {"topic": inp.topic, "captions": suggest_captions(inp.topic, inp.n)}

@app.post("/generate_meme")
def api_generate_meme(inp: MemeGenIn):
    # 1) Generate an image from prompt (or fallback gradient)
    img = generate_image(inp.prompt, negative=inp.negative or "", seed=inp.seed, width=inp.width, height=inp.height)

    # 2) Generate short captions (or fallback)
    caps = suggest_captions(inp.prompt, n=3)
    top = caps[0] if caps else (inp.styleTop or "")
    bottom = caps[1] if len(caps) > 1 else (inp.styleBottom or "")

    # 3) Burn captions meme-style
    out = caption_image(img, top, bottom, FONT_PATH)

    out_name = f"gen_{now_slug()}.png"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    out.save(out_path, "PNG")
    return {"file": out_name, "download": f"/download/{out_name}", "usedCaptions": {"top": top, "bottom": bottom}}


class SmartMemeIn(BaseModel):
    imageDataUri: str
    topText: Optional[str] = ""
    bottomText: Optional[str] = ""
    showContext: bool = True
    maxObjects: int = 6
    width: Optional[int] = None    # optional: resize source
    height: Optional[int] = None

# --- add this route below your other endpoints ---
@app.post("/smart_meme")
def smart_meme(inp: SmartMemeIn):
    # 1) Load image (and optional resize)
    base = Image.open(io.BytesIO(data_uri_to_bytes(inp.imageDataUri))).convert("RGB")
    if inp.width and inp.height:
        base = base.resize((inp.width, inp.height), Image.LANCZOS)

    # 2) Auto-fit captions by expanding canvas as needed (no overlap)
    captioned = auto_caption_canvas(
        base,
        top_text=inp.topText or "",
        bottom_text=inp.bottomText or "",
        font_path=FONT_PATH,
    )

    # 3) Extract contextual objects and build right-side panel
    if inp.showContext:
        thumbs = extract_context_objects(base, max_items=max(1, min(inp.maxObjects, 12)))
        composed = layout_with_context_panel(captioned, thumbs)
    else:
        composed = captioned

    out_name = f"smart_{now_slug()}.png"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    composed.save(out_path, "PNG")
    return {"file": out_name, "download": f"/download/{out_name}"}