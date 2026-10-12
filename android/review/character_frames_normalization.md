# Character Animation Frame Package Normalization Report

**Application:** `VirtualAssistant`  
**Project:** `troLyAo_ani`  
**Task:** Production Preparation & Normalization of Six-State Anime Character Frames  
**Date:** 07/10/2026  
**Status:** Completed & Validated  

---

## 1. Executive Summary

This report documents the deterministic normalization and production preparation of the six-state 2D anime character frame animation package for the Android `VirtualAssistant` application. Following the initial technical audit, the master frames have been transformed from raw 1024 × 1024 PNGs into an optimized, visually unified, memory-safe Android package at **768 × 768 WebP** format.

### Key Accomplishments:
1. **Memory & Size Optimization:** Total package compressed footprint was reduced from **75.89 MB** down to **6.20 MB** (a **91.8% reduction**, saving 69.69 MB). Decoded bitmap memory per frame dropped from **4.00 MB** to **2.25 MiB** (2,359,296 bytes), completely eliminating the Android `OutOfMemoryError` (OOM) risk.
2. **Deterministic Action-Level Normalization:** Applied exactly one uniform geometric scale and translation per action. Natural character motion, body sway, head tilts, and hair dynamics within each sequence are 100% preserved with zero per-frame auto-crop jitter.
3. **Visual Scale & Baseline Alignment (`talk` vs `idle`):** The ~13% character shrink and 129 px drop in the raw `talk` assets was corrected. The normalized `talk` envelope matches `idle` within **0.41% in height** (739 px vs 736 px), **0.93% in width** (432 px vs 428 px), and baselines align within **3 pixels** at $y \approx 755$.
4. **Glitched Frame Exclusion:** Stray frame `happy/character_happy_0016.png` was safely omitted. The output `happy` action cleanly terminates on neutral resting frame `character_happy_0015.webp`. Frames `0001` through `0015` remain unrenumbered.
5. **Edge Margin & Safety:** All 140 output frames maintain generous transparent margins ($x \in [158, 610]$, $y \in [16, 755]$). **Zero pixels touch canvas edges**, preventing clipping across all screen densities.
6. **Zero Source Mutation:** All 141 files in `character_frames_original/` were verified byte-identical before and after processing via SHA-256 cryptographic hashes.

---

## 2. Input and Output Paths

- **Source Input Directory:**  
  `D:\nam5\semester_1\advance_android\01_trolyAI\character_frames_original`
- **Normalized Output Directory:**  
  `D:\nam5\semester_1\advance_android\01_trolyAI\character_frames_android`  
  *(Created as a sibling directory outside the Git repository)*
- **Android Project Directory:**  
  `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani\android`

---

## 3. Confirmation of Original Immutability

It is formally certified that:
- **Zero source images** in `character_frames_original/` were renamed, moved, overwritten, modified, or deleted.
- File `character_happy_0016.png` remains intact in the original package.
- All 141 source file SHA-256 hashes were recorded in the manifest and independently verified after processing.
- No files were copied into Android `app/src/main/res/` during this task.
- No Kotlin, Gradle, manifest, backend code, Git branch, or Git commit was touched.

---

## 4. Processing Method

The preparation pipeline used a deterministic, action-level envelope normalization method:

1. **Union Bounding Box Extraction:**  
   For each action, all included frames were decoded as 32-bit RGBA. An alpha bounding box ($\alpha > 0$) was calculated for every frame. The union bounding box $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$ across all included frames was computed to establish the action's movement envelope.
2. **Target Canvas Specifications:**  
   - Canvas Dimensions: $768 \times 768\text{ px}$ (Square, 1:1)
   - Target Visible Union Height: Approximately $740\text{ px}$
   - Horizontal Alignment: Center ($x_{\text{center}} = 384.0\text{ px}$)
   - Vertical Anchor: Bottom ($y_{\text{bottom}} \approx 755\text{ px}$)
   - Transparent Margins: Approximately $12\text{ px}$ bottom margin ($y \in [756, 767]$) and $16\text{ px}$ top margin ($y \in [0, 15]$).
3. **Action-Level Uniform Transform:**  
   - Scale factor: $S = \frac{\text{Target Visible Height}}{\text{Union Bounding Height}} = \frac{740.0}{\text{Union Height}}$
   - Source frame $1024 \times 1024$ resized uniformly using Lanczos resampling to $W_{\text{new}} = \text{round}(1024 \times S)$, $H_{\text{new}} = \text{round}(1024 \times S)$.
   - Paste offset $X$: $\text{round}(384.0 - X_{\text{union\_center}} \times S_{\text{actual}})$
   - Paste offset $Y$: $\text{round}(755 - Y_{\text{union\_bottom}} \times S_{\text{actual}})$
   - Composited onto a blank, transparent $768 \times 768$ RGBA canvas.
4. **Encoding:**  
   Saved as individual WebP frames with alpha channel preserved at `quality=92`, `method=6`.

---

## 5. Transformation Table

Every frame within an action received the exact same transformation parameters:

| Action | Input frames | Output frames | Source union box | Scale | X offset | Y offset | Output visible box | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `idle` | 32 | 32 | `[213, 0, 810, 1022]` ($598 \times 1023$) | `0.723363` | `+14 px` | `+15 px` | `[170, 17, 597, 752]` ($428 \times 736$) | Normalized |
| `thinking` | 30 | 30 | `[222, 5, 817, 1023]` ($596 \times 1019$) | `0.726202` | `+7 px` | `+12 px` | `[171, 18, 597, 755]` ($427 \times 738$) | Normalized |
| `talk` | 19 | 19 | `[252, 133, 771, 1023]` ($520 \times 891$) | `0.830527` | `-41 px` | `-94 px` | `[168, 17, 599, 755]` ($432 \times 739$) | Normalized & Rescaled |
| `happy` | 16 | 15 | `[213, 5, 810, 1023]` ($598 \times 1019$) | `0.726202` | `+12 px` | `+12 px` | `[168, 18, 597, 755]` ($430 \times 738$) | Normalized (`0016` omitted) |
| `sad` | 21 | 21 | `[216, 0, 850, 1023]` ($635 \times 1024$) | `0.722656` | `-1 px` | `+16 px` | `[158, 19, 610, 755]` ($453 \times 737$) | Normalized |
| `surprised` | 23 | 23 | `[213, 0, 814, 1023]` ($602 \times 1024$) | `0.722656` | `+13 px` | `+16 px` | `[169, 16, 600, 755]` ($432 \times 740$) | Normalized |

---

## 6. Output Inventory

| Action | Frames | Format | Dimensions | Alpha | Compressed size | Edge clipping | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `idle` | 32 | WebP | $768 \times 768$ | RGBA | 1.49 MB (1,559,296 B) | None ($0\text{ touches}$) | Ready |
| `thinking` | 30 | WebP | $768 \times 768$ | RGBA | 1.20 MB (1,254,276 B) | None ($0\text{ touches}$) | Ready |
| `talk` | 19 | WebP | $768 \times 768$ | RGBA | 0.88 MB (921,582 B) | None ($0\text{ touches}$) | Ready |
| `happy` | 15 | WebP | $768 \times 768$ | RGBA | 0.71 MB (744,162 B) | None ($0\text{ touches}$) | Ready |
| `sad` | 21 | WebP | $768 \times 768$ | RGBA | 0.88 MB (922,168 B) | None ($0\text{ touches}$) | Ready |
| `surprised` | 23 | WebP | $768 \times 768$ | RGBA | 1.05 MB (1,103,766 B) | None ($0\text{ touches}$) | Ready |
| **Total** | **140** | **WebP** | **$768 \times 768$** | **100% RGBA** | **6.20 MB (6,505,250 B)** | **0 edge touches** | **Ready for Integration** |

---

## 7. Talk-Versus-Idle Comparison

A critical finding of the audit was that the source `talk` frames were drawn ~13% smaller, with the character head beginning 129 px lower than in `idle`. The envelope normalization successfully unified both states:

| Metric | `idle` (Normalized) | `talk` (Normalized) | Difference | Requirement Limit | Verification |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Visible Union Height** | 736 px | 739 px | **0.41%** (3 px) | $\le 3.0\%$ | **PASSED** |
| **Visible Union Width** | 428 px | 432 px | **0.93%** (4 px) | $\le 5.0\%$ | **PASSED** |
| **Horizontal Center ($x$)** | 383.5 px | 383.5 px | **0.0 px** (Exact) | Centered at 384 | **PASSED** |
| **Bottom Baseline ($y$)** | 752 px | 755 px | **3 px** (0.39%) | Lower feet aligned | **PASSED** |
| **Top Margin ($y$)** | 17 px | 17 px | **0 px** | Top aligned | **PASSED** |

Visual inspection confirms that transitioning between `IDLE` and `TALKING` maintains consistent character size, position, and feet grounding without layout jumps or shrinking.

---

## 8. Happy Frame Exclusion

- **Original Count:** 16 frames (`character_happy_0001.png` to `character_happy_0016.png`).
- **Anomalous Frame:** `character_happy_0016.png` was an errant duplicate of intermediate smile frame `0007`/`0012` (`6c7f6300`), which caused the animation to pop back into a smile for 66 ms after already settling into neutral rest at frames `0013`–`0015` (`9a02bda6`).
- **Resolution:**
  - Frame `character_happy_0016` was completely excluded from the output package.
  - Output contains exactly 15 frames: `character_happy_0001.webp` through `character_happy_0015.webp`.
  - Frames `0001` through `0015` retain their original numbering.
  - The animation now concludes seamlessly on neutral resting frame `0015`, ready to transition directly into `idle`.

---

## 9. Transparency and Edge Validation

All 140 output WebP frames were individually inspected via pixel analysis:
- **Dimensions:** Exactly $768 \times 768\text{ px}$ across 100% of frames.
- **Color Mode:** 32-bit RGBA with full alpha transparency.
- **Fully Transparent Frames:** 0 detected.
- **Canvas Edge Touching:** **0 frames touch any canvas edge**.
  - Left edge ($x = 0$): Clear. Minimum visible $x$ is 158 px ($> 157\text{ px}$ margin).
  - Right edge ($x = 767$): Clear. Maximum visible $x$ is 610 px ($> 157\text{ px}$ margin).
  - Top edge ($y = 0$): Clear. Minimum visible $y$ is 16 px ($16\text{ px}$ transparent margin).
  - Bottom edge ($y = 767$): Clear. Maximum visible $y$ is 755 px ($12\text{ px}$ transparent margin).
- No hair, ears, feet, or clothing elements are clipped.

---

## 10. Output Size and Memory Estimate

### 10.1 Storage / APK Footprint
- **Original 1024 × 1024 PNG Package:** 79,579,705 bytes (**75.89 MB**)
- **Normalized 768 × 768 WebP Package:** 6,505,250 bytes (**6.20 MB**)
- **Storage Reduction:** **-91.82%** (69.69 MB reduction)

### 10.2 Decoded Memory at Runtime
In Android, the uncompressed decoded memory for an active $768 \times 768$ Bitmap in `ARGB_8888` configuration is:
$$\text{Memory per Frame} = 768 \times 768 \times 4\text{ bytes} = 2,359,296\text{ bytes} \approx 2.25\text{ MiB}$$

In the Jetpack Compose animation player, only the active frame (or at most two frames in a double-buffered crossfade) is decoded simultaneously in RAM:
- Single Active Frame: **2.25 MiB**
- Double-Buffered Pair: **4.50 MiB**

This represents a negligible memory footprint that operates comfortably within any Android device's heap allocation, eliminating frame drops, stutter, and garbage collection churn.

---

## 11. Android Compatibility

1. **Android Resource Naming:**
   Every output file strictly conforms to Android drawable resource naming constraints (`^[a-z0-9_]+\.webp$`):
   - `character_idle_0001.webp` .. `character_idle_0032.webp`
   - `character_thinking_0001.webp` .. `character_thinking_0030.webp`
   - `character_talk_0001.webp` .. `character_talk_0019.webp`
   - `character_happy_0001.webp` .. `character_happy_0015.webp`
   - `character_sad_0001.webp` .. `character_sad_0021.webp`
   - `character_surprised_0001.webp` .. `character_surprised_0023.webp`
2. **MinSDK 26 Compatibility:**
   - Android has natively supported transparent WebP since Android 4.2.1 (API level 17).
   - The application target is `minSdk = 26` (Android 8.0 Oreo).
   - WebP assets placed into `res/drawable-nodpi/` decode natively via `BitmapFactory` and Jetpack Compose `painterResource()` without requiring third-party decoders or fallbacks.

---

## 12. Preview Artifact Paths

Two high-resolution visual inspection artifacts were generated and saved in the project review directory:

1. **Idle vs Talk Normalized Comparison:**  
   `troLyAo_ani/android/review/idle_talk_normalized_comparison.png`  
   ([idle_talk_normalized_comparison.png](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/review/idle_talk_normalized_comparison.png))  
   *Renders `character_idle_0001.webp` and `character_talk_0001.webp` side-by-side on identical $768 \times 768$ checkerboard canvases with horizontal baseline and head-height guide lines.*
2. **Normalized States Contact Sheet:**  
   `troLyAo_ani/android/review/normalized_states_contact_sheet.png`  
   ([normalized_states_contact_sheet.png](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/review/normalized_states_contact_sheet.png))  
   *Displays a 12-cell grid showcasing the rest frame and peak action frame for all six normalized states on checkerboard backgrounds.*

---

## 13. Files Created

| Path | Purpose |
|:---|:---|
| `troLyAo_ani/android/tools/prepare_character_frames.py` | Reusable, deterministic action-level normalization script. |
| `troLyAo_ani/android/tools/validate_normalized_frames.py` | 18-point automated validation script. |
| `troLyAo_ani/android/tools/generate_normalization_previews.py` | Visual preview and contact sheet generator. |
| `character_frames_android/` (140 `.webp` files) | Production-ready normalized frame package. |
| `character_frames_android/normalization_manifest.json` | Complete cryptographic hash manifest and transform metadata. |
| `troLyAo_ani/android/review/idle_talk_normalized_comparison.png` | Idle vs Talk scale & baseline visual comparison artifact. |
| `troLyAo_ani/android/review/normalized_states_contact_sheet.png` | Six-state contact sheet overview artifact. |
| `troLyAo_ani/android/review/character_frames_normalization.md` | This comprehensive normalization report. |

---

## 14. Remaining Issues

| Issue ID | Severity | Affected Files | Evidence | Impact | Recommended Action |
|:---|:---:|:---|:---|:---|:---|
| None | `INFO` | None | All 18 automated criteria passed. | Zero operational impact. | Proceed to integration planning when ready. |

There are **zero remaining blockers, high-severity defects, or unresolved discrepancies**.

---

## 15. Final Verdict

```text
================================================================================
FINAL VERDICT: READY TO COPY INTO ANDROID RESOURCES
================================================================================
```

### Rationale:
The normalized package at `character_frames_android/` fulfills 100% of the functional, geometric, memory, and format requirements. When the development team is ready for integration, the `.webp` files can be safely copied directly into `troLyAo_ani/android/app/src/main/res/drawable-nodpi/`.

---
*End of Normalization Report.*
