# backend/app/ai.py
import os, random
from typing import List, Optional

# ----- Optional LLM for captions (kept as before) -----
_USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if _USE_OPENAI:
    try:
        from openai import OpenAI
        _openai = OpenAI()
    except Exception:
        _USE_OPENAI = False

PUNCH_SEEDS = [
    "me trying to {topic}",
    "{topic}: expectation vs reality",
    "POV: {topic} chose you",
    "the face you make when {topic}",
    "breaking news: {topic} strikes again",
    "scientists discover {topic}, society in shambles"
]

def suggest_captions(topic: str, n: int = 5) -> List[str]:
    topic = (topic or "life").strip()
    if _USE_OPENAI:
        try:
            resp = _openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content": f"Write {n} short, punchy meme captions (<=8 words) about: {topic}. Return as a simple numbered list."}],
                temperature=0.9
            )
            text = resp.choices[0].message.content
            lines = [l.split(". ",1)[-1].strip("-• ").strip() for l in text.splitlines() if l.strip()]
            out = [l for l in lines if l][:n]
            if out: return out
        except Exception:
            pass
    random.seed(topic)
    picks = random.sample(PUNCH_SEEDS, k=min(n, len(PUNCH_SEEDS)))
    return [p.format(topic=topic) for p in picks]

# ----- Image generation (free & local with Diffusers) -----
_DIFF_MODEL = os.getenv("DIFFUSERS_MODEL", "stabilityai/sdxl-turbo")
_DIFF_SCHED = os.getenv("DIFFUSERS_SCHEDULER", "lcm").lower()   # lcm|euler|ddim
_DEVICE_REQ = os.getenv("DEVICE", "auto").lower()               # auto|cuda|mps|directml|cpu
_DTYPE_REQ  = os.getenv("TORCH_DTYPE", "auto").lower()
_STEPS      = int(os.getenv("DIFFUSERS_STEPS", 6))
_GUIDANCE   = float(os.getenv("DIFFUSERS_GUIDANCE", 0.0))

_USE_DIFFUSERS = False
_pipe = None

def _resolve_device_dtype():
    import torch
    # device
    if _DEVICE_REQ == "cuda" and torch.cuda.is_available():
        device = "cuda"
    elif _DEVICE_REQ == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    elif _DEVICE_REQ == "directml":
        # torch-directml uses "dml" device string
        try:
            import torch_directml # noqa
            device = "dml"
        except Exception:
            device = "cpu"
    elif _DEVICE_REQ == "cpu":
        device = "cpu"
    else:
        device = "cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")

    # dtype
    if _DTYPE_REQ in ("float16", "fp16"):
        dtype = torch.float16
    elif _DTYPE_REQ in ("bfloat16","bf16"):
        dtype = torch.bfloat16
    elif _DTYPE_REQ in ("float32","fp32"):
        dtype = torch.float32
    else:
        # auto
        if device in ("cuda","mps","dml"):
            dtype = torch.float16
        else:
            dtype = torch.float32
    return device, dtype

def _init_pipe():
    global _USE_DIFFUSERS, _pipe
    if _pipe is not None:
        return
    try:
        from diffusers import StableDiffusionPipeline, AutoPipelineForText2Image, LCMScheduler, EulerAncestralDiscreteScheduler, DPMSolverMultistepScheduler
        import torch

        device, dtype = _resolve_device_dtype()

        # Prefer AutoPipeline (handles SDXL-Turbo / SD-Turbo / Lightning)
        pipe = AutoPipelineForText2Image.from_pretrained(
            _DIFF_MODEL,
            torch_dtype=dtype,
            safety_checker=None
        )

        # Scheduler selection optimized for speed
        sched = _DIFF_SCHED
        if sched == "lcm":
            pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
        elif sched == "euler":
            pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
        elif sched == "ddim":
            # DPMSolver is generally faster/better than vanilla DDIM; keep as alt
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        else:
            # default fallback: LCM for speed
            from diffusers import LCMScheduler
            pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)

        # Move pipe to device (MPS / CUDA / DML / CPU)
        pipe = pipe.to(device)

        # Some DirectML stacks dislike enable_xformers; keep off by default
        # try:
        #     pipe.enable_xformers_memory_efficient_attention()
        # except Exception: pass

        _pipe = pipe
        _USE_DIFFUSERS = True
    except Exception as e:
        _USE_DIFFUSERS = False
        _pipe = None

def generate_image(prompt: str, negative: str = "", seed: Optional[int] = None, width: int = 768, height: int = 768):
    """
    Returns a PIL.Image. If diffusers not available, returns a stylized fallback.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import numpy as np, math, random as rnd

    _init_pipe()
    if _USE_DIFFUSERS and _pipe:
        try:
            import torch
            g = None
            if seed is not None:
                # Generator depends on device
                dev, _ = _resolve_device_dtype()
                if dev == "cuda":
                    g = torch.Generator("cuda").manual_seed(seed)
                elif dev == "mps":
                    g = torch.Generator("cpu").manual_seed(seed)  # mps gen must be cpu
                else:
                    g = torch.Generator("cpu").manual_seed(seed)

            # For Turbo/Lightning/LCM, CFG should be low (0–1)
            guidance = _GUIDANCE if _GUIDANCE is not None else 0.0
            steps = max(1, min(20, _STEPS))

            img = _pipe(
                prompt=prompt,
                negative_prompt=(negative or None),
                num_inference_steps=steps,
                guidance_scale=guidance,
                width=width, height=height,
                generator=g
            ).images[0]
            return img
        except Exception:
            pass

    # ---- Fallback: gradient canvas with prompt label ----
    W, H = width, height
    base = Image.new("RGB", (W, H))
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        for x in range(W):
            arr[y, x] = (
                (30 + (x*7 + y*3) % 120),
                (40 + (x*5 + y*9) % 120),
                (60 + (x*2 + y*6) % 120),
            )
    base = Image.fromarray(arr, "RGB").filter(ImageFilter.GaussianBlur(1.0))
    draw = ImageDraw.Draw(base)
    try:
        font = ImageFont.truetype("arial.ttf", size=40)
    except:
        font = ImageFont.load_default()
    msg = (prompt or "vibe").strip()[:48]
    tw, th = draw.textlength(msg, font=font), font.size + 6
    draw.rectangle([20, H-th-40, 20+tw+20, H-20], fill=(0,0,0,128))
    draw.text((30, H-th-35), msg, fill=(255,255,255), font=font)
    return base
