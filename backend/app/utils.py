import base64, io, time, math
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

def now_slug() -> str:
    return str(int(time.time() * 1000))

def data_uri_to_bytes(data_uri: str) -> bytes:
    if data_uri.startswith("data:"):
        return base64.b64decode(data_uri.split(",", 1)[1])
    return base64.b64decode(data_uri)

def bytes_to_data_uri(b: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(b).decode("ascii")

def load_font(path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except Exception:
        return ImageFont.load_default()

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def caption_image(img: Image.Image, top_text: str = "", bottom_text: str = "", font_path: Optional[str] = None) -> Image.Image:
    W, H = img.size
    margin = int(0.04 * H)
    draw = ImageDraw.Draw(img)
    base_size = max(16, int(H * 0.08))
    font = load_font(font_path, base_size)

    def draw_block(lines, y):
        for line in lines:
            w = draw.textlength(line, font=font)
            x = (W - w) // 2
            draw.text((x, y), line, fill=(0, 0, 0), font=font, stroke_width=4, stroke_fill=(0, 0, 0))
            draw.text((x, y), line, fill=(255, 255, 255), font=font)
            y += int(font.size * 1.1)

    max_text_width = int(W * 0.95)
    if top_text:
        top_lines = wrap_text(draw, top_text.upper(), font, max_text_width)
        y = margin
        draw_block(top_lines, y)

    if bottom_text:
        bottom_lines = wrap_text(draw, bottom_text.upper(), font, max_text_width)
        total_h = int(len(bottom_lines) * font.size * 1.1)
        y = H - total_h - margin
        draw_block(bottom_lines, y)

    return img

def combine_side_by_side(img1: Image.Image, img2: Image.Image, vertical: bool = False, gap: int = 12, bg=(20,20,20)) -> Image.Image:
    if vertical:
        w = max(img1.width, img2.width)
        h = img1.height + gap + img2.height
        out = Image.new("RGB", (w, h), bg)
        out.paste(img1, ((w - img1.width)//2, 0))
        out.paste(img2, ((w - img2.width)//2, img1.height + gap))
    else:
        w = img1.width + gap + img2.width
        h = max(img1.height, img2.height)
        out = Image.new("RGB", (w, h), bg)
        out.paste(img1, (0, (h - img1.height)//2))
        out.paste(img2, (img1.width + gap, (h - img2.height)//2))
    return out


def measure_wrapped(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> Tuple[list[str], int, int]:
    """Wrap text to fit max_width; return (lines, total_width, total_height)."""
    lines = wrap_text(draw, (text or "").upper(), font, max_width)
    if not lines:
        return [], 0, 0
    line_h = int(font.size * 1.1)
    total_h = line_h * len(lines)
    total_w = max(int(draw.textlength(line, font=font)) for line in lines)
    return lines, total_w, total_h

def auto_caption_canvas(
    img: Image.Image,
    top_text: str = "",
    bottom_text: str = "",
    font_path: str | None = None,
    max_ratio_for_text: float = 0.26,
    side_padding_ratio: float = 0.04,
    gap_ratio: float = 0.02,
) -> Image.Image:
    """
    Return a new image where the original is centered and canvas is grown vertically
    as needed to fit top/bottom text without overlap. Font size adapts to width.
    """
    W, H = img.size
    side_pad = int(W * side_padding_ratio)
    gap = int(H * gap_ratio)

    # Start with a generous font size and shrink until it fits within max width and max height budget
    max_text_h = int(H * max_ratio_for_text)  # budget for top and bottom each (when present)
    draw_probe = ImageDraw.Draw(img)
    target_font_size = max(16, int(H * 0.09))
    font = load_font(font_path, target_font_size)

    # Binary search font size to satisfy width/height constraints
    lo, hi = 12, target_font_size
    best = font
    for _ in range(12):
        mid = (lo + hi) // 2
        test_font = load_font(font_path, mid)
        top_lines, top_w, top_h = measure_wrapped(draw_probe, top_text, test_font, W - 2 * side_pad)
        bot_lines, bot_w, bot_h = measure_wrapped(draw_probe, bottom_text, test_font, W - 2 * side_pad)
        fits_w = top_w <= (W - 2*side_pad) and bot_w <= (W - 2*side_pad)
        fits_h = (not top_text or top_h <= max_text_h) and (not bottom_text or bot_h <= max_text_h)
        if fits_w and fits_h:
            best = test_font
            lo = mid + 1
        else:
            hi = mid - 1
    font = best

    # Recompute with chosen font
    top_lines, top_w, top_h = measure_wrapped(draw_probe, top_text, font, W - 2*side_pad)
    bot_lines, bot_w, bot_h = measure_wrapped(draw_probe, bottom_text, font, W - 2*side_pad)

    add_top = top_h + (gap if top_h else 0)
    add_bot = bot_h + (gap if bot_h else 0)
    new_H = H + add_top + add_bot
    canvas = Image.new("RGB", (W, new_H), (20, 20, 20))
    draw = ImageDraw.Draw(canvas)

    # Paste original centered vertically between text blocks
    canvas.paste(img, (0, add_top))

    # Draw top block
    y = int((add_top - top_h) / 2) if top_h else 0
    for line in top_lines:
        tw = int(draw.textlength(line, font=font))
        x = (W - tw) // 2
        draw.text((x, y), line, fill=(0,0,0), font=font, stroke_width=4, stroke_fill=(0,0,0))
        draw.text((x, y), line, fill=(255,255,255), font=font)
        y += int(font.size * 1.1)

    # Draw bottom block
    y = H + add_top + int((add_bot - bot_h) / 2) if bot_h else 0
    for line in bot_lines:
        tw = int(draw.textlength(line, font=font))
        x = (W - tw) // 2
        draw.text((x, y), line, fill=(0,0,0), font=font, stroke_width=4, stroke_fill=(0,0,0))
        draw.text((x, y), line, fill=(255,255,255), font=font)
        y += int(font.size * 1.1)

    return canvas

# -------- Context object extraction (YOLOv8n if available; fallback crops) --------
def extract_context_objects(img: Image.Image, max_items: int = 6) -> list[Image.Image]:
    """
    Returns a list of cropped object thumbnails from the image.
    Uses YOLOv8n if available; otherwise returns simple center crops as fallback.
    """
    # Try YOLO
    try:
        from ultralytics import YOLO
        import numpy as np
        model = YOLO("yolov8n.pt")  # downloads if not present
        # Convert PIL -> BGR np for yolov8 (it accepts PIL/np; we'll use np)
        arr = np.array(img.convert("RGB"))
        results = model(arr, verbose=False)[0]
        boxes = []
        for b in results.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            conf = float(b.conf[0].item()) if hasattr(b, "conf") else 0.0
            boxes.append((conf, (x1, y1, x2, y2)))
        boxes.sort(reverse=True, key=lambda t: t[0])
        crops = []
        for _, (x1, y1, x2, y2) in boxes[:max_items]:
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img.width, x2), min(img.height, y2)
            if x2 > x1 and y2 > y1:
                crops.append(img.crop((x1, y1, x2, y2)))
        if crops:
            return crops
    except Exception:
        pass

    # Fallback: generate some simple centered crops
    W, H = img.size
    crops = []
    for i in range(max_items):
        # progressively smaller centered crops
        scale = 0.7 - i * 0.08
        scale = max(0.3, scale)
        cw, ch = int(W * scale), int(H * scale)
        x1 = (W - cw) // 2
        y1 = (H - ch) // 2
        crops.append(img.crop((x1, y1, x1 + cw, y1 + ch)))
    return crops

def layout_with_context_panel(main_img: Image.Image, thumbs: list[Image.Image], panel_width_ratio: float = 0.35, gap: int = 10) -> Image.Image:
    """
    Compose main image on the left and a vertical panel of object thumbnails on the right.
    """
    if not thumbs:
        return main_img
    W, H = main_img.size
    panel_w = max(220, int(W * panel_width_ratio))
    # Prepare thumbs to fit panel width
    prepared = []
    for t in thumbs:
        th = int(panel_w * t.height / t.width)
        prepared.append(t.resize((panel_w, th), Image.LANCZOS))
    panel_h = sum(t.height for t in prepared) + gap * (len(prepared) - 1)
    out_h = max(H, panel_h)
    out = Image.new("RGB", (W + gap + panel_w, out_h), (18,18,18))
    out.paste(main_img, (0, (out_h - H)//2))
    y = (out_h - panel_h)//2
    for t in prepared:
        out.paste(t, (W + gap, y))
        y += t.height + gap
    return out