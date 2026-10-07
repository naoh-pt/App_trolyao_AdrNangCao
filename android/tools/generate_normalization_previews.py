#!/usr/bin/env python3
"""
generate_normalization_previews.py
----------------------------------
Generates visual review artifacts for the normalized character frames:
1. troLyAo_ani/android/review/normalized_states_contact_sheet.png
2. troLyAo_ani/android/review/idle_talk_normalized_comparison.png
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make_checkerboard(width: int, height: int, cell_size: int = 16, c1=(240, 240, 245), c2=(220, 220, 228)) -> Image.Image:
    img = Image.new("RGBA", (width, height), c1)
    draw = ImageDraw.Draw(img)
    for y in range(0, height, cell_size):
        for x in range(0, width, cell_size):
            if ((x // cell_size) + (y // cell_size)) % 2 == 1:
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=c2)
    return img

def main():
    out_dir = Path("character_frames_android")
    rev_dir = Path("troLyAo_ani/android/review")
    rev_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # 1. idle_talk_normalized_comparison.png
    # Two full 768x768 checkerboard canvases side-by-side
    # ---------------------------------------------------------
    pad = 40
    header_h = 60
    footer_h = 80
    total_w = pad + 768 + pad + 768 + pad
    total_h = header_h + 768 + footer_h

    comp_img = Image.new("RGBA", (total_w, total_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(comp_img)

    # Title header
    draw.text((pad, 15), "Normalized Character Alignment & Scale Comparison: IDLE vs TALK", fill=(20, 20, 20, 255))
    draw.text((pad, 35), "Target Canvas: 768 x 768 px | Uniform Action Transform | WebP (quality 92, method 6)", fill=(100, 100, 100, 255))

    # Canvas 1: IDLE
    c1_x = pad
    c1_y = header_h
    cb1 = make_checkerboard(768, 768)
    idle_frame = Image.open(out_dir / "idle" / "character_idle_0001.webp").convert("RGBA")
    cb1.paste(idle_frame, (0, 0), idle_frame)
    comp_img.paste(cb1, (c1_x, c1_y))

    # Canvas 2: TALK
    c2_x = pad + 768 + pad
    c2_y = header_h
    cb2 = make_checkerboard(768, 768)
    talk_frame = Image.open(out_dir / "talk" / "character_talk_0001.webp").convert("RGBA")
    cb2.paste(talk_frame, (0, 0), talk_frame)
    comp_img.paste(cb2, (c2_x, c2_y))

    # Horizontal guide lines across both canvases
    # Baseline guide line (at y = header_h + 755)
    base_guide_y = header_h + 755
    draw.line([(pad - 20, base_guide_y), (total_w - pad + 20, base_guide_y)], fill=(255, 0, 0, 220), width=2)
    draw.text((pad, base_guide_y + 4), "Shared Bottom Baseline: y = 755 px (Transparent margin = 12 px)", fill=(200, 0, 0, 255))

    # Head top guide line (at y = header_h + 17)
    top_guide_y = header_h + 17
    draw.line([(pad - 20, top_guide_y), (total_w - pad + 20, top_guide_y)], fill=(0, 150, 0, 220), width=2)
    draw.text((pad, top_guide_y - 15), "Shared Head Top: y = 17 px (Transparent margin = 16 px)", fill=(0, 130, 0, 255))

    # Center vertical lines
    draw.line([(c1_x + 384, c1_y), (c1_x + 384, c1_y + 768)], fill=(0, 100, 255, 120), width=1)
    draw.line([(c2_x + 384, c2_y), (c2_x + 384, c2_y + 768)], fill=(0, 100, 255, 120), width=1)

    # Footers
    draw.text((c1_x, header_h + 768 + 10), "IDLE (character_idle_0001.webp)", fill=(20, 20, 20, 255))
    draw.text((c1_x, header_h + 768 + 28), "Union Box: w=428 px, h=736 px | Center x=383.5 | Baseline y=752", fill=(80, 80, 80, 255))
    draw.text((c1_x, header_h + 768 + 46), "Scale: 0.72336 (resized to 741x741, offset=(14, 15))", fill=(100, 100, 100, 255))

    draw.text((c2_x, header_h + 768 + 10), "TALK (character_talk_0001.webp) [NORMALIZED]", fill=(20, 20, 20, 255))
    draw.text((c2_x, header_h + 768 + 28), "Union Box: w=432 px, h=739 px | Center x=383.5 | Baseline y=755", fill=(80, 80, 80, 255))
    draw.text((c2_x, header_h + 768 + 46), "Scale: 0.83053 (resized to 850x850, offset=(-41, -94)) | Delta: H=0.41%, W=0.93%", fill=(0, 120, 0, 255))

    comp_path = rev_dir / "idle_talk_normalized_comparison.png"
    comp_img.save(comp_path, "PNG")
    print(f"Saved comparison to: {comp_path}")

    # ---------------------------------------------------------
    # 2. normalized_states_contact_sheet.png
    # Grid of key frames from all 6 states
    # ---------------------------------------------------------
    key_items = [
        ("idle - Frame 1 (Rest)", out_dir / "idle" / "character_idle_0001.webp"),
        ("idle - Frame 16 (Peak)", out_dir / "idle" / "character_idle_0016.webp"),
        ("thinking - Frame 1 (Rest)", out_dir / "thinking" / "character_thinking_0001.webp"),
        ("thinking - Frame 16 (Peak)", out_dir / "thinking" / "character_thinking_0016.webp"),
        ("talk - Frame 1 (Closed)", out_dir / "talk" / "character_talk_0001.webp"),
        ("talk - Frame 10 (Open)", out_dir / "talk" / "character_talk_0010.webp"),
        ("happy - Frame 1 (Rest)", out_dir / "happy" / "character_happy_0001.webp"),
        ("happy - Frame 10 (Apex)", out_dir / "happy" / "character_happy_0010.webp"),
        ("sad - Frame 1 (Rest)", out_dir / "sad" / "character_sad_0001.webp"),
        ("sad - Frame 10 (Slouch)", out_dir / "sad" / "character_sad_0010.webp"),
        ("surprised - Frame 1 (Rest)", out_dir / "surprised" / "character_surprised_0001.webp"),
        ("surprised - Frame 14 (Peak)", out_dir / "surprised" / "character_surprised_0014.webp"),
    ]

    cell_size = 256
    cols = 4
    rows = 3
    grid_pad = 20
    cell_lbl_h = 35

    grid_w = grid_pad + cols * (cell_size + grid_pad)
    grid_h = grid_pad + rows * (cell_size + cell_lbl_h + grid_pad)

    sheet_img = Image.new("RGBA", (grid_w, grid_h), (250, 250, 252, 255))
    sheet_draw = ImageDraw.Draw(sheet_img)

    for idx, (label, img_p) in enumerate(key_items):
        r = idx // cols
        c = idx % cols
        x = grid_pad + c * (cell_size + grid_pad)
        y = grid_pad + r * (cell_size + cell_lbl_h + grid_pad)

        cb = make_checkerboard(cell_size, cell_size, cell_size=8)
        frame_im = Image.open(img_p).convert("RGBA")
        thumb = frame_im.resize((cell_size, cell_size), Image.Resampling.LANCZOS)
        cb.paste(thumb, (0, 0), thumb)
        sheet_img.paste(cb, (x, y))

        sheet_draw.text((x + 2, y + cell_size + 6), label, fill=(30, 30, 30, 255))

    sheet_path = rev_dir / "normalized_states_contact_sheet.png"
    sheet_img.save(sheet_path, "PNG")
    print(f"Saved contact sheet to: {sheet_path}")

if __name__ == "__main__":
    main()
