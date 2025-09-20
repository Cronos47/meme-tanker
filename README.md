# 🎭 MemeForge Studio

**AI-powered Meme Generator & Editor** — make memes that *actually slap* in seconds.  
From quick captions to karaoke dubs, from AI-generated images to context-object smart panels — all in one sleek app.

---

## ✨ Features

### 🔹 Meme Creation
- **Quick Meme** — classic top/bottom caption editor
- **Smart Meme** — auto-resizes canvas for captions + detects contextual objects and displays them side-panel style
- **Remix Mode** — combine two images side-by-side or stacked
- **Meme Karaoke** — add captions + your voice (or a tone) and export as MP4 with subtitles

### 🔹 AI Magic
- **AI Meme Generator**  
  - Generate a meme image from a text prompt (via Stable Diffusion Turbo / Lightning / LCM)  
  - Auto-suggest captions using OpenAI or fallback heuristics  
- **Caption Suggestions** — “one-liner” punchlines for your topic
- **Context Object Extraction** — detect objects in your image (YOLOv8n) and show them in a separate panel for more clarity/fun

### 🔹 Tech Stack
- **Backend:** FastAPI + Pillow + MoviePy + (optional) Diffusers, YOLOv8, OpenAI  
- **Frontend:** Next.js (App Router) + TailwindCSS + Framer Motion  
- **Optional AI Models:**  
  - [SDXL Turbo](https://huggingface.co/stabilityai/sdxl-turbo)  
  - [SDXL Lightning](https://huggingface.co/ByteDance/SDXL-Lightning)  
  - [YOLOv8n](https://github.com/ultralytics/ultralytics)  
  - OpenAI GPT (for text captions)

---

## Backend Setup

```cd backend/```

```python -m venv .meme-forge```

### Windows
```.meme-forge\Scripts\Activate.Ps1```

### macOS/Linux
```source .meme-forge/bin/activate```

```pip install -r requirements.txt```
```cp .env.sample .env```

## Run the API:
```uvicorn app.main:app --reload --port 8081```

## Frontend Setup
```cd frontend/```

```npm install```

```cp .env.local.example .env.local```

```npm run dev```

```Output: https://localhost:3000```
