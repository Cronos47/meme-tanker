"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8081";

function toDataUri(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result as string);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

type TabKey = "gen" | "quick" | "karaoke" | "remix" | "smart";

export default function Page() {
  const [tab, setTab] = useState<TabKey>("gen");

  const tabs: { key: TabKey; label: string }[] = useMemo(
    () => [
      { key: "gen", label: "AI Generator" },
      { key: "quick", label: "Quick Meme" },
      { key: "karaoke", label: "Meme Karaoke" },
      { key: "remix", label: "Remix Mode" },
      { key: "smart", label: "Smart Meme" },
    ],
    []
  );

  return (
    <main className="max-w-6xl mx-auto p-6 md:p-10">
      <header className="flex items-center justify-between mb-8">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
          MemeForge <span className="text-accent">Studio</span>
        </h1>
        <a href="https://ffmpeg.org/" target="_blank" className="btn text-sm" rel="noreferrer">Need FFmpeg?</a>
      </header>

      <div className="card p-2 md:p-3">
        <nav className="relative flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`relative z-10 px-4 py-2 rounded-xl transition ${tab === t.key ? "text-white" : "text-white/70 hover:text-white"}`}
            >
              {t.label}
              {tab === t.key && (
                <motion.span
                  layoutId="pill"
                  className="absolute inset-0 -z-10 rounded-xl"
                  style={{ background: "linear-gradient(135deg, rgba(110,231,255,.25), rgba(167,139,250,.25))", border: "1px solid rgba(255,255,255,.15)" }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
            </button>
          ))}
        </nav>

        <div className="mt-4 md:mt-6">
          <AnimatePresence mode="wait">
            {tab === "gen" && <MotionWrap><AIGenerator /></MotionWrap>}
            {tab === "quick" && <MotionWrap><QuickMeme /></MotionWrap>}
            {tab === "karaoke" && <MotionWrap><Karaoke /></MotionWrap>}
            {tab === "remix" && <MotionWrap><Remix /></MotionWrap>}
            {tab === "smart" && <MotionWrap><SmartMeme /></MotionWrap>}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}

function SmartMeme() {
  const [imgUri, setImgUri] = useState<string | null>(null);
  const [top, setTop] = useState("WHEN YOU SHIP ON FRIDAY");
  const [bottom, setBottom] = useState("SEE YOU ON MONDAY");
  const [showContext, setShowContext] = useState(true);
  const [maxObjects, setMaxObjects] = useState(5);
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function generate() {
    if (!imgUri) return;
    setBusy(true); setResult(null);
    try {
      const r = await fetch(`${API}/smart_meme`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          imageDataUri: imgUri,
          topText: top,
          bottomText: bottom,
          showContext,
          maxObjects
        })
      });
      const data = await r.json();
      const dl = await fetch(`${API}${data.download}`);
      const payload = await dl.json();
      setResult(payload.dataUri);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Inputs</h2>
        <DropZone label="Click or Drag an Image" accept="image/*" onPick={setImgUri} preview={imgUri} />
        <div className="mt-4 grid gap-3">
          <input className="input" placeholder="Top text" value={top} onChange={e=>setTop(e.target.value)} />
          <input className="input" placeholder="Bottom text" value={bottom} onChange={e=>setBottom(e.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={showContext} onChange={e=>setShowContext(e.target.checked)} />
            Show context objects panel
          </label>
          <label className="flex items-center gap-2 text-sm">
            Max objects:
            <input className="input" type="number" min={1} max={12} value={maxObjects} onChange={e=>setMaxObjects(Number(e.target.value))} />
          </label>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={generate} className="btn">Generate Smart Meme</button>
          {busy && <Loading />}
        </div>
      </div>
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Result</h2>
        {!result && <p className="text-white/60">No output yet.</p>}
        {result && (
          <>
            <a className="btn text-sm" href={result} download="smart-meme.png">Download PNG</a>
            <img src={result} className="mt-4 rounded-xl border border-white/10 w-full" />
          </>
        )}
      </div>
    </div>
  );
}


function MotionWrap({ children }: { children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
      {children}
    </motion.div>
  );
}

function Loading({ label = "Working..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-white/80">
      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" fill="none" />
        <path d="M21 12a9 9 0 0 1-9 9" stroke="currentColor" strokeWidth="3" fill="none" />
      </svg>
      {label}
    </div>
  );
}

/* ---------------- AI Generator ---------------- */
function AIGenerator() {
  const [prompt, setPrompt] = useState("a raccoon CEO presenting quarterly nuts earnings, cinematic");
  const [negative, setNegative] = useState("");
  const [seed, setSeed] = useState<number | undefined>(undefined);
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [usedCaps, setUsedCaps] = useState<{top?: string; bottom?: string} | null>(null);

  async function generate() {
    setBusy(true); setResult(null); setUsedCaps(null);
    try {
      const r = await fetch(`${API}/generate_meme`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt, negative,
          seed: seed ?? null,
          width: 1024, height: 1024
        })
      });
      const data = await r.json();
      const dl = await fetch(`${API}${data.download}`);
      const payload = await dl.json();
      setResult(payload.dataUri);
      setUsedCaps(data.usedCaptions);
    } finally {
      setBusy(false);
    }
  }

  async function suggest() {
    const r = await fetch(`${API}/suggest_captions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: prompt, n: 5 })
    });
    const data = await r.json();
    alert("Suggestions:\n\n" + data.captions.map((c: string) => "• " + c).join("\n"));
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Prompt</h2>
        <textarea className="input min-h-28" value={prompt} onChange={e=>setPrompt(e.target.value)} />
        <div className="grid md:grid-cols-3 gap-3 mt-3">
          <input className="input" placeholder="Negative prompt (optional)" value={negative} onChange={e=>setNegative(e.target.value)} />
          <input className="input" placeholder="Seed (optional)" value={seed ?? ""} onChange={e=>setSeed(e.target.value ? Number(e.target.value) : undefined)} />
          <button className="btn" onClick={suggest}>Suggest captions</button>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={generate} className="btn">Generate Meme</button>
          {busy && <Loading />}
        </div>
        {usedCaps && (
          <p className="text-xs text-white/70 mt-3">Used captions — Top: “{usedCaps.top}”, Bottom: “{usedCaps.bottom}”</p>
        )}
        {!process.env.NEXT_PUBLIC_API_BASE_URL && (
          <p className="text-xs text-yellow-300 mt-2">Note: Using local fallbacks if AI keys/models are not configured.</p>
        )}
      </div>

      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Result</h2>
        {!result && <p className="text-white/60">No output yet.</p>}
        {result && (
          <>
            <a className="btn text-sm" href={result} download="ai-meme.png">Download PNG</a>
            <img src={result} className="mt-4 rounded-xl border border-white/10" />
          </>
        )}
      </div>
    </div>
  );
}

/* ---------------- Existing tabs (unchanged) ---------------- */
function QuickMeme() {
  const [imgUri, setImgUri] = useState<string | null>(null);
  const [top, setTop] = useState("");
  const [bottom, setBottom] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true); setResult(null);
    try {
      const r = await fetch(`${API}/quick_meme`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ imageDataUri: imgUri, topText: top, bottomText: bottom })
      });
      const data = await r.json();
      const dl = await fetch(`${API}${data.download}`);
      const payload = await dl.json();
      setResult(payload.dataUri);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Source</h2>
        <DropZone label="Click or Drag an Image" accept="image/*" onPick={setImgUri} preview={imgUri} />
        <div className="mt-4 grid gap-3">
          <input className="input" placeholder="Top text" value={top} onChange={e=>setTop(e.target.value)} />
          <input className="input" placeholder="Bottom text" value={bottom} onChange={e=>setBottom(e.target.value)} />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={generate} className="btn">Generate PNG</button>
          {busy && <Loading />}
        </div>
      </div>
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Result</h2>
        {!result && <p className="text-white/60">No output yet.</p>}
        {result && (
          <>
            <a className="btn text-sm" href={result} download="meme.png">Download PNG</a>
            <img src={result} className="mt-4 rounded-xl border border-white/10" />
          </>
        )}
      </div>
    </div>
  );
}

function Karaoke() {
  const [imgUri, setImgUri] = useState<string | null>(null);
  const [audioUri, setAudioUri] = useState<string | null>(null);
  const [caption, setCaption] = useState("When the meme hits too hard");
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true); setResult(null);
    try {
      const r = await fetch(`${API}/karaoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ imageDataUri: imgUri, audioDataUri: audioUri, caption })
      });
      const data = await r.json();
      const dl = await fetch(`${API}${data.download}`);
      const payload = await dl.json();
      setResult(payload.dataUri);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Inputs</h2>
        <div className="grid gap-4">
          <DropZone label="Click or Drag an Image" accept="image/*" onPick={setImgUri} preview={imgUri} />
          <DropZone label="Click or Drag an Audio (WAV/MP3)" accept="audio/*" onPick={setAudioUri} preview={audioUri} />
          <textarea className="input min-h-28" value={caption} onChange={e=>setCaption(e.target.value)} />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={generate} className="btn">Generate MP4</button>
          {!audioUri && <span className="text-xs text-white/60">No audio? A tone will be used.</span>}
          {busy && <Loading />}
        </div>
      </div>
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Result</h2>
        {!result && <p className="text-white/60">No output yet.</p>}
        {result && (
          <>
            <a className="btn text-sm" href={result} download="meme.mp4">Download MP4</a>
            <video src={result} controls className="mt-4 rounded-xl border border-white/10 w-full" />
          </>
        )}
      </div>
    </div>
  );
}

function Remix() {
  const [leftUri, setLeft] = useState<string | null>(null);
  const [rightUri, setRight] = useState<string | null>(null);
  const [vertical, setVertical] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true); setResult(null);
    try {
      const r = await fetch(`${API}/remix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ leftDataUri: leftUri, rightDataUri: rightUri, vertical })
      });
      const data = await r.json();
      const dl = await fetch(`${API}${data.download}`);
      const payload = await dl.json();
      setResult(payload.dataUri);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Inputs</h2>
        <div className="grid gap-4">
          <DropZone label="Left Image" accept="image/*" onPick={setLeft} preview={leftUri} />
          <DropZone label="Right Image" accept="image/*" onPick={setRight} preview={rightUri} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={vertical} onChange={e=>setVertical(e.target.checked)} />
            Stack vertically
          </label>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={generate} className="btn">Generate Remix PNG</button>
          {busy && <Loading />}
        </div>
      </div>
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Result</h2>
        {!result && <p className="text-white/60">No output yet.</p>}
        {result && (
          <>
            <a className="btn text-sm" href={result} download="remix.png">Download PNG</a>
            <img src={result} className="mt-4 rounded-xl border border-white/10" />
          </>
        )}
      </div>
    </div>
  );
}

function DropZone({
  label,
  accept,
  onPick,
  preview
}: {
  label: string;
  accept: string;
  onPick: (uri: string) => void;
  preview?: string | null;
}) {
  return (
    <div
      className="drop cursor-pointer"
      onDragOver={(e) => e.preventDefault()}
      onDrop={async (e) => {
        e.preventDefault();
        const f = e.dataTransfer.files?.[0];
        if (!f) return;
        if (!f.type.match(accept.replace("*", ".*"))) return;
        onPick(await toDataUri(f));
      }}
      onClick={async () => {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = accept;
        input.onchange = async () => {
          const file = (input.files?.[0]);
          if (!file) return;
          onPick(await toDataUri(file));
        };
        input.click();
      }}
    >
      <p className="text-white/80">{label}</p>
      {preview && accept.startsWith("image") && (
        <img src={preview} alt="preview" className="mt-3 rounded-xl border border-white/10 max-h-64 mx-auto" />
      )}
      {preview && accept.startsWith("audio") && (
        <audio src={preview} controls className="mt-3 w-full" />
      )}
    </div>
  );
}
