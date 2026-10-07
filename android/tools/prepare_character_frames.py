#!/usr/bin/env python3
"""
prepare_character_frames.py
---------------------------
Deterministic normalization and optimization tool for character frame animations.

Normalizes raw 1024x1024 anime character frames to 768x768 WebP assets for Android:
- Action-level uniform scaling (preserves intra-action motion and inter-frame timing)
- Normalizes character visual scale across actions (corrects smaller 'talk' scale)
- Aligns horizontal center to canvas center (x = 384)
- Anchors bottom to y = 755 leaving safe transparent margins (~12-16px)
- Excludes errant frame happy/character_happy_0016.png
- Encodes to transparent WebP (quality 92, method 6)
- Leaves source directories completely untouched (read-only)
- Generates normalization_manifest.json with complete metadata and hashes

Usage:
    python prepare_character_frames.py <input_dir> <output_dir> [--force] [--json-manifest <path>]

Example:
    python tools/prepare_character_frames.py ../../character_frames_original ../../character_frames_android
"""

import sys
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


ACTIONS = ["idle", "thinking", "talk", "happy", "sad", "surprised"]
EXPECTED_COUNTS = {
    "idle": 32,
    "thinking": 30,
    "talk": 19,
    "happy": 16,
    "sad": 21,
    "surprised": 23
}
EXCLUDED_FRAMES = {
    "happy": ["character_happy_0016.png"]
}

TARGET_CANVAS_WIDTH = 768
TARGET_CANVAS_HEIGHT = 768
TARGET_VISIBLE_HEIGHT = 740.0
TARGET_BOTTOM_Y = 755
TARGET_CENTER_X = 384.0
WEBP_QUALITY = 92
WEBP_METHOD = 6


def natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_alpha_bbox(img: Image.Image) -> Tuple[int, int, int, int]:
    """Returns (min_x, min_y, max_x, max_y) where alpha > 0, or None if fully transparent."""
    img_rgba = img.convert("RGBA")
    arr = np.array(img_rgba)
    alpha = arr[:, :, 3]
    nz = np.argwhere(alpha > 0)
    if len(nz) == 0:
        return None
    min_y = int(np.min(nz[:, 0]))
    max_y = int(np.max(nz[:, 0]))
    min_x = int(np.min(nz[:, 1]))
    max_x = int(np.max(nz[:, 1]))
    return (min_x, min_y, max_x, max_y)


def run_preparation(input_path: Path, output_path: Path, force: bool = False) -> Dict[str, Any]:
    if not PIL_AVAILABLE:
        print("ERROR: Pillow and numpy are required to run prepare_character_frames.py.", file=sys.stderr)
        sys.exit(1)

    if not input_path.is_dir():
        print(f"ERROR: Input directory does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Safety check on output directory
    if output_path.exists():
        entries = list(output_path.iterdir())
        if entries and not force:
            print(f"ERROR: Destination directory '{output_path}' already exists and contains {len(entries)} items.", file=sys.stderr)
            print("To prevent accidental data loss, the tool refused to run without --force.", file=sys.stderr)
            sys.exit(1)

    # Verify input action directories
    for action in ACTIONS:
        act_dir = input_path / action
        if not act_dir.is_dir():
            print(f"ERROR: Missing expected action directory: {act_dir}", file=sys.stderr)
            sys.exit(1)
        pngs = [p for p in act_dir.glob("*.png")]
        expected = EXPECTED_COUNTS[action]
        if len(pngs) != expected:
            print(f"ERROR: Action '{action}' expected {expected} PNG files, found {len(pngs)}.", file=sys.stderr)
            sys.exit(1)

    # Create destination directories
    output_path.mkdir(parents=True, exist_ok=True)
    for action in ACTIONS:
        (output_path / action).mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Any] = {
        "metadata": {
            "input_package": str(input_path.resolve()),
            "output_package": str(output_path.resolve()),
            "format": "WEBP",
            "canvas_dimensions": [TARGET_CANVAS_WIDTH, TARGET_CANVAS_HEIGHT],
            "target_visible_height": TARGET_VISIBLE_HEIGHT,
            "target_bottom_y": TARGET_BOTTOM_Y,
            "target_center_x": TARGET_CENTER_X,
            "quality": WEBP_QUALITY,
            "method": WEBP_METHOD,
            "excluded_frames": EXCLUDED_FRAMES
        },
        "actions": {},
        "totals": {}
    }

    total_input_frames = 0
    total_output_frames = 0
    total_input_bytes = 0
    total_output_bytes = 0

    print("=" * 80)
    print("STARTING CHARACTER FRAME NORMALIZATION")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("=" * 80)

    for action in ACTIONS:
        act_in_dir = input_path / action
        act_out_dir = output_path / action
        raw_files = sorted(list(act_in_dir.glob("*.png")), key=lambda p: natural_sort_key(p.name))
        
        # Filter excluded frames
        excluded_for_act = EXCLUDED_FRAMES.get(action, [])
        included_files = [f for f in raw_files if f.name not in excluded_for_act]
        
        action_input_bytes = sum(f.stat().st_size for f in raw_files)
        total_input_bytes += action_input_bytes
        total_input_frames += len(raw_files)
        total_output_frames += len(included_files)

        # 1. Analyze action union bounding box across included frames
        print(f"\nProcessing action '{action}' ({len(included_files)} included / {len(raw_files)} total)...")
        union_min_x, union_min_y = 99999, 99999
        union_max_x, union_max_y = -1, -1

        input_hashes = {}
        for f in raw_files:
            f_hash = compute_sha256(f)
            input_hashes[f.name] = f_hash
            if f.name in excluded_for_act:
                continue

            with Image.open(f) as img:
                bbox = compute_alpha_bbox(img)
                if bbox is not None:
                    min_x, min_y, max_x, max_y = bbox
                    union_min_x = min(union_min_x, min_x)
                    union_min_y = min(union_min_y, min_y)
                    union_max_x = max(union_max_x, max_x)
                    union_max_y = max(union_max_y, max_y)

        union_w = union_max_x - union_min_x + 1
        union_h = union_max_y - union_min_y + 1
        union_cx = (union_min_x + union_max_x) / 2.0

        # 2. Calculate uniform transform parameters for this action
        scale = TARGET_VISIBLE_HEIGHT / float(union_h)
        new_w = round(1024 * scale)
        new_h = round(1024 * scale)
        actual_scale_x = new_w / 1024.0
        actual_scale_y = new_h / 1024.0

        paste_x = round(TARGET_CENTER_X - union_cx * actual_scale_x)
        paste_y = round(TARGET_BOTTOM_Y - union_max_y * actual_scale_y)

        # 3. Process every included frame
        output_hashes = {}
        out_union_min_x, out_union_min_y = 99999, 99999
        out_union_max_x, out_union_max_y = -1, -1
        edge_touch_count = 0
        action_output_bytes = 0

        for f in included_files:
            with Image.open(f) as src_img:
                src_rgba = src_img.convert("RGBA")
                resized = src_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                canvas = Image.new("RGBA", (TARGET_CANVAS_WIDTH, TARGET_CANVAS_HEIGHT), (0, 0, 0, 0))
                canvas.paste(resized, (paste_x, paste_y), resized)

                out_bbox = compute_alpha_bbox(canvas)
                if out_bbox is None:
                    print(f"ERROR: Frame {f.name} rendered completely transparent!", file=sys.stderr)
                    sys.exit(1)

                ox1, oy1, ox2, oy2 = out_bbox
                out_union_min_x = min(out_union_min_x, ox1)
                out_union_min_y = min(out_union_min_y, oy1)
                out_max_x_cur = max(out_union_max_x, ox2)
                out_union_max_x = out_max_x_cur
                out_max_y_cur = max(out_union_max_y, oy2)
                out_union_max_y = out_max_y_cur

                if ox1 == 0 or oy1 == 0 or ox2 == (TARGET_CANVAS_WIDTH - 1) or oy2 == (TARGET_CANVAS_HEIGHT - 1):
                    edge_touch_count += 1
                    print(f"WARNING: Frame {f.name} touches canvas edge at [{ox1}, {oy1}, {ox2}, oy2]!", file=sys.stderr)

                # Save as WebP
                out_filename = f.stem + ".webp"
                out_file_path = act_out_dir / out_filename
                canvas.save(out_file_path, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)

                out_size = out_file_path.stat().st_size
                action_output_bytes += out_size
                output_hashes[out_filename] = compute_sha256(out_file_path)

        total_output_bytes += action_output_bytes
        out_visible_w = out_union_max_x - out_union_min_x + 1
        out_visible_h = out_union_max_y - out_union_min_y + 1
        out_visible_cx = (out_union_min_x + out_union_max_x) / 2.0

        manifest["actions"][action] = {
            "input_frame_count": len(raw_files),
            "output_frame_count": len(included_files),
            "excluded_frames": excluded_for_act,
            "source_union_box": {
                "min_x": union_min_x,
                "min_y": union_min_y,
                "max_x": union_max_x,
                "max_y": union_max_y,
                "width": union_w,
                "height": union_h,
                "center_x": union_cx
            },
            "transform": {
                "scale": round(scale, 6),
                "resized_dimensions": [new_w, new_h],
                "paste_offset_x": paste_x,
                "paste_offset_y": paste_y
            },
            "output_visible_box": {
                "min_x": out_union_min_x,
                "min_y": out_union_min_y,
                "max_x": out_union_max_x,
                "max_y": out_union_max_y,
                "width": out_visible_w,
                "height": out_visible_h,
                "center_x": round(out_visible_cx, 2),
                "baseline_y": out_union_max_y
            },
            "edge_touch_count": edge_touch_count,
            "compressed_size_bytes": action_output_bytes,
            "input_hashes": input_hashes,
            "output_hashes": output_hashes
        }

        print(f"  Union In:   [{union_min_x}, {union_min_y}, {union_max_x}, {union_max_y}] ({union_w}x{union_h})")
        print(f"  Transform:  scale={scale:.5f}, size=({new_w}, {new_h}), paste=({paste_x}, {paste_y})")
        print(f"  Visible Out:[{out_union_min_x}, {out_union_min_y}, {out_union_max_x}, {out_union_max_y}] ({out_visible_w}x{out_visible_h}), bottom={out_union_max_y}")
        print(f"  Disk Size:  {action_input_bytes / (1024*1024):.2f} MB PNG -> {action_output_bytes / (1024*1024):.2f} MB WebP")

    manifest["totals"] = {
        "input_frame_count": total_input_frames,
        "output_frame_count": total_output_frames,
        "input_compressed_bytes": total_input_bytes,
        "output_compressed_bytes": total_output_bytes,
        "compression_ratio_pct": round((total_output_bytes / total_input_bytes) * 100.0, 2),
        "decoded_memory_per_frame_bytes": TARGET_CANVAS_WIDTH * TARGET_CANVAS_HEIGHT * 4
    }

    # Write manifest
    manifest_path = output_path / "normalization_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 80)
    print("NORMALIZATION COMPLETE")
    print(f"Total Input Frames:  {total_input_frames}")
    print(f"Total Output Frames: {total_output_frames}")
    print(f"Source Size:         {total_input_bytes / (1024*1024):.2f} MB")
    print(f"Optimized WebP Size: {total_output_bytes / (1024*1024):.2f} MB ({manifest['totals']['compression_ratio_pct']}% of original)")
    print(f"Manifest written to: {manifest_path}")
    print("=" * 80)

    return manifest


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python prepare_character_frames.py <input_dir> <output_dir> [--force]")
        sys.exit(1)

    in_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    force_run = "--force" in sys.argv

    run_preparation(in_dir, out_dir, force=force_run)
