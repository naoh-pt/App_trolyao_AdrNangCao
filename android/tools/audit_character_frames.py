#!/usr/bin/env python3
"""
audit_character_frames.py
-------------------------
Read-only audit script for character PNG frame animations in Android VirtualAssistant.

Usage:
    python audit_character_frames.py <path_to_frame_package> [--json <output_json>]

Example:
    python tools/audit_character_frames.py ../../character_frames_original
"""

import sys
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Check if PIL is available
try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


ACTIONS = ["idle", "thinking", "talk", "happy", "sad", "surprised"]
ANDROID_RES_NAME_PATTERN = re.compile(r"^[a-z0-9_]+\.png$")
DIGIT_PATTERN = re.compile(r"\d+")


def natural_sort_key(s: str):
    """Sort strings containing numbers naturally (e.g. frame_2 before frame_10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def extract_frame_number(filename: str):
    """Extract numeric suffix/frame number from filename."""
    matches = DIGIT_PATTERN.findall(filename)
    if matches:
        return int(matches[-1]), matches[-1]
    return None, None


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def audit_frame_package(package_dir: Path) -> Dict[str, Any]:
    if not package_dir.is_dir():
        raise ValueError(f"Package directory not found: {package_dir}")

    results = {
        "package_dir": str(package_dir.resolve()),
        "actions_found": [],
        "actions_missing": [],
        "inventory": {},
        "naming_validation": {},
        "png_validity": {},
        "canvas_consistency": {},
        "alignment_and_jitter": {},
        "duplicates_and_suspicious": {},
        "performance_and_memory": {},
        "summary": {}
    }

    subdirs = {p.name: p for p in package_dir.iterdir() if p.is_dir()}
    for action in ACTIONS:
        if action in subdirs:
            results["actions_found"].append(action)
        else:
            results["actions_missing"].append(action)

    total_png_count = 0
    total_compressed_bytes = 0
    all_canvas_dimensions = set()
    global_file_hashes = {}  # hash -> list of (action, filename)
    global_pixel_hashes = {}

    for action in ACTIONS:
        if action not in subdirs:
            continue
        
        action_path = subdirs[action]
        all_entries = list(action_path.iterdir())
        
        # Identify files
        png_files = [p for p in all_entries if p.is_file() and p.name.lower().endswith(".png")]
        non_png_files = [p.name for p in all_entries if p.is_file() and not p.name.lower().endswith(".png")]
        subfolders = [p.name for p in all_entries if p.is_dir()]
        hidden_or_temp = [p.name for p in all_entries if p.name.startswith(".") or p.name.startswith("~")]

        # Natural sort PNG files
        png_files.sort(key=lambda p: natural_sort_key(p.name))
        count = len(png_files)
        total_png_count += count

        # File sizes
        file_sizes = [p.stat().st_size for p in png_files]
        action_compressed_bytes = sum(file_sizes)
        total_compressed_bytes += action_compressed_bytes

        min_size = min(file_sizes) if file_sizes else 0
        max_size = max(file_sizes) if file_sizes else 0
        avg_size = (action_compressed_bytes / count) if count > 0 else 0

        # Numbering and sequence
        frame_numbers = []
        zero_padded_samples = []
        gaps = []
        
        for p in png_files:
            num, raw_digits = extract_frame_number(p.name)
            if num is not None:
                frame_numbers.append(num)
                zero_padded_samples.append(raw_digits)

        seq_start = frame_numbers[0] if frame_numbers else None
        seq_end = frame_numbers[-1] if frame_numbers else None
        is_zero_padded = all(len(s) > 1 and s.startswith("0") for s in zero_padded_samples) if zero_padded_samples else False
        expected_pad_len = len(zero_padded_samples[0]) if zero_padded_samples else 0

        # Check gaps
        if frame_numbers:
            expected_range = list(range(seq_start, seq_end + 1))
            missing_nums = set(expected_range) - set(frame_numbers)
            if missing_nums:
                gaps = sorted(list(missing_nums))

        # Check duplicate filenames (case variations)
        seen_names = {}
        dup_names = []
        for p in all_entries:
            low = p.name.lower()
            if low in seen_names:
                dup_names.append((p.name, seen_names[low]))
            else:
                seen_names[low] = p.name

        # Inventory record
        results["inventory"][action] = {
            "png_count": count,
            "first_file": png_files[0].name if png_files else None,
            "last_file": png_files[-1].name if png_files else None,
            "seq_start": seq_start,
            "seq_end": seq_end,
            "starts_at_zero": seq_start == 0 if seq_start is not None else False,
            "is_zero_padded": is_zero_padded,
            "padding_length": expected_pad_len,
            "gaps": gaps,
            "duplicate_filenames": dup_names,
            "non_png_files": non_png_files,
            "subfolders": subfolders,
            "hidden_or_temp": hidden_or_temp,
            "total_bytes": action_compressed_bytes,
            "min_bytes": min_size,
            "max_bytes": max_size,
            "avg_bytes": avg_size
        }

        # Naming compatibility
        naming_issues = []
        recommended_names = []
        for idx, p in enumerate(png_files):
            fname = p.name
            issues = []
            if not ANDROID_RES_NAME_PATTERN.match(fname):
                if any(c.isupper() for c in fname):
                    issues.append("uppercase")
                if " " in fname:
                    issues.append("space")
                if "-" in fname:
                    issues.append("hyphen")
                if "(" in fname or ")" in fname:
                    issues.append("parentheses")
                if fname.count(".") > 1:
                    issues.append("multiple_dots")
                if re.search(r"[^\x00-\x7F]", fname):
                    issues.append("non_ascii_or_vietnamese")
            num, _ = extract_frame_number(fname)
            if num is None:
                issues.append("missing_frame_number")

            if issues:
                naming_issues.append({"file": fname, "issues": issues})
            
            # Form recommended name
            rec_num = f"{idx + 1:04d}"
            recommended_names.append(f"character_{action}_{rec_num}.png")

        results["naming_validation"][action] = {
            "issues_count": len(naming_issues),
            "issues": naming_issues,
            "example_recommended": recommended_names[0] if recommended_names else None,
            "mapping_status": f"folder '{action}' -> application state " + ("TALKING" if action == "talk" else action.upper())
        }

        # PNG validity and canvas inspection
        validity_records = []
        action_dimensions = set()
        action_modes = set()
        action_bboxes = []
        action_transparent_ratios = []
        consecutive_identical_bytes = []
        consecutive_identical_pixels = []
        prev_file_hash = None
        prev_pixel_hash = None
        prev_img_data = None

        for idx, p in enumerate(png_files):
            f_hash = sha256_file(p)
            global_file_hashes.setdefault(f_hash, []).append((action, p.name))
            
            if prev_file_hash and f_hash == prev_file_hash:
                consecutive_identical_bytes.append((png_files[idx-1].name, p.name))
            prev_file_hash = f_hash

            # Inspect binary header
            with open(p, "rb") as f:
                sig = f.read(8)
                is_png_sig = (sig == b"\x89PNG\r\n\x1a\n")

            rec = {
                "file": p.name,
                "has_png_sig": is_png_sig,
                "can_decode": False,
                "format": None,
                "width": 0,
                "height": 0,
                "mode": None,
                "has_alpha": False,
                "transparent_pixel_pct": 0.0,
                "fully_transparent": False,
                "fully_opaque": False,
                "bbox": None,
                "touches_edges": []
            }

            if PIL_AVAILABLE:
                try:
                    with Image.open(p) as img:
                        rec["format"] = img.format
                        rec["width"], rec["height"] = img.size
                        rec["mode"] = img.mode
                        rec["can_decode"] = True
                        action_dimensions.add(img.size)
                        all_canvas_dimensions.add(img.size)
                        action_modes.add(img.mode)

                        # Decode pixel data to check alpha and bbox
                        img_rgba = img.convert("RGBA")
                        arr = np.array(img_rgba)
                        alpha = arr[:, :, 3]

                        # Alpha analysis
                        total_pixels = img.size[0] * img.size[1]
                        zero_alpha_pixels = int(np.sum(alpha == 0))
                        pct_trans = (zero_alpha_pixels / total_pixels) * 100.0
                        rec["transparent_pixel_pct"] = round(pct_trans, 2)
                        rec["has_alpha"] = ("A" in img.mode) or (pct_trans > 0)
                        rec["fully_transparent"] = (zero_alpha_pixels == total_pixels)
                        rec["fully_opaque"] = (zero_alpha_pixels == 0 and np.all(alpha == 255))
                        action_transparent_ratios.append(pct_trans)

                        # Bounding box of visible content (alpha > 0)
                        non_zero_coords = np.argwhere(alpha > 0)
                        if len(non_zero_coords) > 0:
                            # non_zero_coords is [[y, x], ...]
                            min_y = int(np.min(non_zero_coords[:, 0]))
                            max_y = int(np.max(non_zero_coords[:, 0]))
                            min_x = int(np.min(non_zero_coords[:, 1]))
                            max_x = int(np.max(non_zero_coords[:, 1]))
                            
                            bbox = {
                                "left": min_x,
                                "top": min_y,
                                "right": max_x,
                                "bottom": max_y,
                                "width": max_x - min_x + 1,
                                "height": max_y - min_y + 1,
                                "center_x": round((min_x + max_x) / 2.0, 2),
                                "center_y": round((min_y + max_y) / 2.0, 2),
                                "baseline": max_y
                            }
                            rec["bbox"] = bbox
                            action_bboxes.append((p.name, bbox))

                            # Edge touching check
                            touches = []
                            if min_x == 0: touches.append("left")
                            if min_y == 0: touches.append("top")
                            if max_x == img.size[0] - 1: touches.append("right")
                            if max_y == img.size[1] - 1: touches.append("bottom")
                            rec["touches_edges"] = touches

                        # Pixel hash
                        pix_hash = hashlib.sha256(arr.tobytes()).hexdigest()
                        global_pixel_hashes.setdefault(pix_hash, []).append((action, p.name))
                        if prev_pixel_hash and pix_hash == prev_pixel_hash:
                            consecutive_identical_pixels.append((png_files[idx-1].name, p.name))
                        prev_pixel_hash = pix_hash

                except Exception as e:
                    rec["decode_error"] = str(e)
            
            validity_records.append(rec)

        results["png_validity"][action] = {
            "all_png_signature": all(r["has_png_sig"] for r in validity_records),
            "all_can_decode": all(r["can_decode"] for r in validity_records),
            "color_modes": list(action_modes),
            "has_alpha": any(r["has_alpha"] for r in validity_records),
            "fully_transparent_count": sum(1 for r in validity_records if r["fully_transparent"]),
            "fully_opaque_count": sum(1 for r in validity_records if r["fully_opaque"]),
            "avg_transparent_pct": round(sum(action_transparent_ratios) / len(action_transparent_ratios), 2) if action_transparent_ratios else 0,
            "min_transparent_pct": min(action_transparent_ratios) if action_transparent_ratios else 0,
            "max_transparent_pct": max(action_transparent_ratios) if action_transparent_ratios else 0,
            "consecutive_identical_bytes": consecutive_identical_bytes,
            "consecutive_identical_pixels": consecutive_identical_pixels
        }

        # Canvas consistency per action
        results["canvas_consistency"][action] = {
            "unique_dimensions": [list(d) for d in action_dimensions],
            "dimension_count": len(action_dimensions),
            "consistent": len(action_dimensions) == 1
        }

        # Alignment and jitter analysis
        jitter_warnings = []
        if action_bboxes:
            for i in range(1, len(action_bboxes)):
                prev_fname, prev_box = action_bboxes[i-1]
                curr_fname, curr_box = action_bboxes[i]
                
                # Check against first dimension width/height
                dim_w, dim_h = list(action_dimensions)[0] if action_dimensions else (1, 1)
                dx = abs(curr_box["center_x"] - prev_box["center_x"])
                dy_base = abs(curr_box["baseline"] - prev_box["baseline"])
                
                dx_pct = (dx / dim_w) * 100.0
                dy_base_pct = (dy_base / dim_h) * 100.0

                if dx_pct > 2.0 or dy_base_pct > 2.0:
                    jitter_warnings.append({
                        "prev_frame": prev_fname,
                        "curr_frame": curr_fname,
                        "dx_pixels": round(dx, 2),
                        "dx_pct": round(dx_pct, 2),
                        "dy_baseline_pixels": round(dy_base, 2),
                        "dy_baseline_pct": round(dy_base_pct, 2)
                    })

            # Check bounding box ranges
            min_l = min(b[1]["left"] for b in action_bboxes)
            max_r = max(b[1]["right"] for b in action_bboxes)
            min_t = min(b[1]["top"] for b in action_bboxes)
            max_b = max(b[1]["bottom"] for b in action_bboxes)
            avg_w = sum(b[1]["width"] for b in action_bboxes) / len(action_bboxes)
            avg_h = sum(b[1]["height"] for b in action_bboxes) / len(action_bboxes)
            edge_touchers = [b[0] for b in action_bboxes if b[1]["left"] == 0 or b[1]["top"] == 0 or b[1]["right"] == (dim_w - 1) or b[1]["bottom"] == (dim_h - 1)]

            results["alignment_and_jitter"][action] = {
                "bbox_overall": {"left": min_l, "top": min_t, "right": max_r, "bottom": max_b},
                "avg_content_width": round(avg_w, 2),
                "avg_content_height": round(avg_h, 2),
                "edge_touching_frames": edge_touchers,
                "jitter_warning_count": len(jitter_warnings),
                "jitter_warnings": jitter_warnings
            }

        # Memory calculations
        # width * height * 4
        sample_w, sample_h = list(action_dimensions)[0] if action_dimensions else (0, 0)
        decoded_per_frame = sample_w * sample_h * 4
        action_decoded_total = decoded_per_frame * count

        results["performance_and_memory"][action] = {
            "compressed_bytes": action_compressed_bytes,
            "decoded_per_frame_bytes": decoded_per_frame,
            "action_simultaneous_decoded_bytes": action_decoded_total,
            "frame_count": count
        }

    # Global duplicates
    global_dup_files = {h: flist for h, flist in global_file_hashes.items() if len(flist) > 1}
    global_dup_pixels = {h: flist for h, flist in global_pixel_hashes.items() if len(flist) > 1}

    results["duplicates_and_suspicious"] = {
        "global_exact_file_duplicates": global_dup_files,
        "global_exact_pixel_duplicates": global_dup_pixels
    }

    # Global canvas consistency
    results["canvas_consistency"]["all_unique_dimensions"] = [list(d) for d in all_canvas_dimensions]
    results["canvas_consistency"]["globally_consistent"] = (len(all_canvas_dimensions) == 1)

    # Total performance & memory
    sample_w, sample_h = list(all_canvas_dimensions)[0] if all_canvas_dimensions else (0, 0)
    full_decoded_total = sample_w * sample_h * 4 * total_png_count
    
    # Risk classification
    # Android bitmap heap limit: typically ~192MB-512MB for modern phones, but individual app RAM target ~100MB-200MB.
    # If all frames decoded at once:
    if full_decoded_total > 300 * 1024 * 1024:
        risk = "CRITICAL"
    elif full_decoded_total > 150 * 1024 * 1024:
        risk = "HIGH"
    elif full_decoded_total > 50 * 1024 * 1024:
        risk = "MODERATE"
    else:
        risk = "LOW"

    results["performance_and_memory"]["full_package"] = {
        "total_frames": total_png_count,
        "total_compressed_bytes": total_compressed_bytes,
        "decoded_per_frame_bytes": sample_w * sample_h * 4,
        "full_package_simultaneous_decoded_bytes": full_decoded_total,
        "risk_classification": risk
    }

    return results


def print_text_summary(res: Dict[str, Any]):
    print("=" * 80)
    print("CHARACTER FRAMES AUDIT SUMMARY")
    print("=" * 80)
    print(f"Package Path: {res['package_dir']}")
    print(f"Actions found: {res['actions_found']}")
    print(f"Actions missing: {res['actions_missing']}")
    print("-" * 80)
    
    print(f"{'Action':<12} | {'Frames':<6} | {'Seq Start-End':<14} | {'Dimensions':<12} | {'Total MB':<9} | {'Decoded MB':<10}")
    print("-" * 80)
    
    for action in ACTIONS:
        inv = res["inventory"].get(action, {})
        dims = res["canvas_consistency"].get(action, {}).get("unique_dimensions", [])
        dim_str = f"{dims[0][0]}x{dims[0][1]}" if dims else "N/A"
        total_mb = inv.get("total_bytes", 0) / (1024 * 1024)
        perf = res["performance_and_memory"].get(action, {})
        decoded_mb = perf.get("action_simultaneous_decoded_bytes", 0) / (1024 * 1024)
        seq = f"{inv.get('seq_start')}-{inv.get('seq_end')}"
        print(f"{action:<12} | {inv.get('png_count', 0):<6} | {seq:<14} | {dim_str:<12} | {total_mb:<9.2f} | {decoded_mb:<10.2f}")
    
    print("-" * 80)
    full = res["performance_and_memory"]["full_package"]
    total_comp_mb = full["total_compressed_bytes"] / (1024 * 1024)
    total_dec_mb = full["full_package_simultaneous_decoded_bytes"] / (1024 * 1024)
    print(f"TOTAL FRAMES: {full['total_frames']}")
    print(f"TOTAL COMPRESSED: {total_comp_mb:.2f} MB")
    print(f"TOTAL DECODED SIMULTANEOUS: {total_dec_mb:.2f} MB")
    print(f"MEMORY RISK CLASSIFICATION: {full['risk_classification']}")
    print(f"GLOBAL CANVAS CONSISTENT: {res['canvas_consistency']['globally_consistent']}")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_character_frames.py <path_to_frame_package> [--json <output.json>]")
        sys.exit(1)

    pkg_dir = Path(sys.argv[1])
    audit_data = audit_frame_package(pkg_dir)

    print_text_summary(audit_data)

    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            out_file = Path(sys.argv[idx + 1])
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(audit_data, f, indent=2)
            print(f"Detailed JSON results written to: {out_file}")
