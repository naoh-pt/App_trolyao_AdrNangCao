# Character Animation Frame Package Audit Report

**Application:** `VirtualAssistant`  
**Project:** `troLyAo_ani`  
**Audit Target:** Six-State PNG Character Frame Package  
**Audit Date:** 06/10/2026  
**Auditor:** Senior Android & Systems Architect  

---

## 1. Executive Summary

This report delivers a comprehensive technical audit of the new six-state 2D character frame animation package for the `VirtualAssistant` Android application within the `troLyAo_ani` project. The package contains sequential PNG frames across six distinct emotional/interaction states: `idle`, `thinking`, `talk`, `happy`, `sad`, and `surprised`.

The objective of this audit is to evaluate whether the character frame assets are structurally valid, visually aligned, memory-safe, and ready for integration into the Jetpack Compose UI without modifying any application code or source assets during the audit.

### Key Audit Findings:
1. **Asset Integrity & Naming (PASSED):** All 141 files across the six directories are authentic 32-bit RGBA PNG images with valid magic signatures and headers. Filenames strictly conform to Android resource naming rules (`character_<action>_<0001..0032>.png`), zero-padded with 4 digits, starting at 1, with zero gaps and zero corruption.
2. **Canvas Uniformity (PASSED):** Every single frame conforms to an exact 1024 × 1024 square canvas.
3. **Memory Footprint & APK Size (CRITICAL BLOCKER):** At 1024 × 1024 resolution and 32-bit ARGB_8888 color depth, each frame requires **4.00 MB** of uncompressed bitmap memory. Simultaneous decoding of all 141 frames demands **564.00 MB** of RAM, which guarantees an instant `OutOfMemoryError` (OOM) crash on Android. Furthermore, the compressed package occupies **75.89 MB**, which is prohibitively large for an Android APK.
4. **Character Scale Discrepancy (HIGH WARNING):** While `idle`, `thinking`, `happy`, `sad`, and `surprised` maintain consistent character bounding heights (~1015 px), the character in `talk` is drawn ~12.4% shorter (889.5 px) and ~13.5% narrower (510.1 px), with the head top starting at row 134 instead of row 0–5. Switching between `idle` and `talk` in a fixed Compose container will produce an abrupt visual shrinking and drop of the character.
5. **Animation Glitch in `happy` (HIGH WARNING):** `character_happy_0016.png` jumps back to an intermediate smiling pose (`6c7f6300`) after the animation has already cleanly returned to neutral at frames 13–15 (`9a02bda6`), causing a 1-frame visual pop before returning to idle.
6. **High Redundancy / Hold Duplication (INFO):** Of the 141 frames, only 84 are globally unique. 57 frames are duplicate holds (e.g., `surprised` has 23 frames but only 7 unique frames, holding key poses for up to 5 consecutive frames).

Based on these findings, the asset package **cannot be dropped directly into the Android application in its raw state**, but is well-structured and readily viable once normalized.

---

## 2. Located Android and Asset Paths

Both required paths were successfully verified on disk without ambiguity:

1. **Android Project Root:**
   - **Path:** `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani\android`
   - **Verification Markers:**
     - `settings.gradle.kts` (root project name: `VirtualAssistant`)
     - `app/build.gradle.kts` (application ID: `com.example.assistant`, minSdk: 26, targetSdk: 34)
     - `app/src/main/` (`AndroidManifest.xml`, `java/`, `res/`)
2. **Character Frame Package Root:**
   - **Path:** `D:\nam5\semester_1\advance_android\01_trolyAI\character_frames_original`
   - **Contained Subdirectories (exactly six):**
     - `idle` (32 frames)
     - `thinking` (30 frames)
     - `talk` (19 frames)
     - `happy` (16 frames)
     - `sad` (21 frames)
     - `surprised` (23 frames)

---

## 3. Final Readiness Verdict

```text
================================================================================
FINAL VERDICT: READY AFTER ASSET NORMALIZATION
================================================================================
```

### Rationale:
- The assets possess clean sequential numbering, zero sequence gaps, valid PNG decoding, full alpha transparency, and consistent 1024 × 1024 canvas bounds.
- However, direct integration is blocked by the **564 MB peak decoded memory** risk, **75.89 MB APK weight**, **~13% character scale mismatch in `talk`**, and a **glitched frame 16 in `happy`**.
- Downscaling assets to 512 × 512, converting to WebP, removing stray frame `happy_0016.png`, aligning `talk` scale, and utilizing frame index mapping will make this package performant and production-ready for Android.

---

## 4. Inventory Table

The inventory below uses natural numeric ordering (`0001` before `0010`):

| Action | Frames | Sequence | Dimensions | Alpha | Compressed size | Decoded memory (Simultaneous) | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `idle` | 32 | `0001`–`0032` | 1024 × 1024 | RGBA (60.1% transparent) | 17.98 MB (18,856,148 B) | 128.00 MB (134,217,728 B) | Normalization Required |
| `thinking` | 30 | `0001`–`0030` | 1024 × 1024 | RGBA (62.9% transparent) | 12.93 MB (13,559,135 B) | 120.00 MB (125,829,120 B) | Normalization Required |
| `talk` | 19 | `0001`–`0019` | 1024 × 1024 | RGBA (69.6% transparent) | 8.52 MB (8,938,124 B) | 76.00 MB (79,691,776 B) | Scale & Norm Required |
| `happy` | 16 | `0001`–`0016` | 1024 × 1024 | RGBA (60.2% transparent) | 9.21 MB (9,654,193 B) | 64.00 MB (67,108,864 B) | Frame 16 Glitch Fix |
| `sad` | 21 | `0001`–`0021` | 1024 × 1024 | RGBA (59.7% transparent) | 9.89 MB (10,368,365 B) | 84.00 MB (88,080,384 B) | Normalization Required |
| `surprised` | 23 | `0001`–`0023` | 1024 × 1024 | RGBA (60.3% transparent) | 17.36 MB (18,203,740 B) | 92.00 MB (96,468,992 B) | Normalization Required |
| **TOTAL** | **141** | **6 sequences** | **1024 × 1024** | **100% RGBA** | **75.89 MB (79,579,705 B)** | **564.00 MB (591,796,864 B)** | **READY AFTER ASSET NORMALIZATION** |

---

## 5. Filename and Sequence Validation

### 5.1 Naming Compliance
Every filename was checked against Android resource naming constraints (`^[a-z0-9_]+\.png$`):
- **Uppercase letters:** 0 detected.
- **Spaces:** 0 detected.
- **Vietnamese / Non-ASCII characters:** 0 detected.
- **Hyphens or parentheses:** 0 detected.
- **Multiple dots:** 0 detected.
- **Ambiguous or missing frame numbers:** 0 detected.
- **Non-PNG files:** 0 detected.
- **Hidden or temporary files (`.DS_Store`, `Thumbs.db`, etc.):** 0 detected.

### 5.2 Sequence Characteristics
- **Sequence indexing:** All actions start strictly at index `1` (`0001`).
- **Padding format:** Every filename uses uniform 4-digit zero-padding (`%04d`).
- **Sequence gaps:** Zero missing numbers across all actions.
- **Action directory mapping:**
  - `character_idle_0001.png` .. `character_idle_0032.png`
  - `character_thinking_0001.png` .. `character_thinking_0030.png`
  - `character_talk_0001.png` .. `character_talk_0019.png`
  - `character_happy_0001.png` .. `character_happy_0016.png`
  - `character_sad_0001.png` .. `character_sad_0021.png`
  - `character_surprised_0001.png` .. `character_surprised_0023.png`

> [!IMPORTANT]
> **State Mapping Confirmation:**  
> The directory `talk` maps directly to application state `TALKING` (`CharacterState.TALKING`).  
> *Note on existing code:* The temporary implementation in `CharacterAvatar.kt` previously looked for `"character_talking"` (`getIdentifier("character_$asset", ...)`). The Compose integration must map `CharacterState.TALKING` to `talk` (`character_talk_xxxx`).

---

## 6. PNG Validity and Transparency

Every file underwent binary signature and pixel decoding verification:
- **Magic Signature:** 141/141 files begin with the standard 8-byte PNG header `\x89PNG\r\n\x1a\n`.
- **Decoder Verification:** 141/141 files decoded cleanly without header warnings, checksum errors, or truncated chunks.
- **Color Mode:** 141/141 images are 32-bit `RGBA` (8 bits per channel).
- **Alpha Channel Analysis:**
  - Full transparency (`alpha == 0`) covers on average **61.9%** of the canvas across all frames.
  - No completely transparent frame exists (`0/141`).
  - No completely opaque frame exists (`0/141`).
- **Corrupted / Invalid Files:** None (`0/141`).

---

## 7. Canvas-Dimension Consistency

1. **Intra-Action Consistency:**
   - Every frame within each folder is identical in canvas dimensions: **1024 × 1024 px**.
2. **Cross-Action Consistency:**
   - Every frame across all six folders is identical: **1024 × 1024 px**.
   - Canvas aspect ratio is uniformly **1:1 (Square)**.
3. **Viewport Sharing:**
   - All frames can technically share a single fixed Compose character viewport (`Modifier.size(side)` or `Modifier.aspectRatio(1f)`).
4. **Layout Jumps:**
   - Because the canvas dimensions are identical, switching states will not trigger Compose layout recalculations or canvas container resize jumps.
   - However, **inner visual content scale jumps** will occur when switching to `talk` (see Section 8).

---

## 8. Alignment and Jitter Analysis

Bounding box analysis (`alpha > 0`) was performed across all 141 frames:

| Action | Min X | Max X | Min Y (Top) | Max Y (Bottom) | Avg Content Width | Avg Content Height | Center X Range | Baseline (Bottom) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `idle` | 213 | 810 | 0 | 1022 | 589.7 px | 1015.1 px | 510.5 – 514.0 px | 1016 – 1022 px |
| `thinking` | 222 | 817 | 5 | 1023 | 527.3 px | 1015.7 px | 519.5 – 540.5 px | 1013 – 1023 px |
| `talk` | 261 | 761 | 133 | 1023 | 510.1 px | 889.5 px | 511.0 – 511.5 px | 1023 px |
| `happy` | 213 | 810 | 5 | 1023 | 592.1 px | 1014.7 px | 510.5 – 512.0 px | 1023 px |
| `sad` | 216 | 850 | 0 | 1023 | 602.6 px | 1022.9 px | 517.0 – 537.0 px | 1023 px |
| `surprised` | 213 | 814 | 0 | 1023 | 587.9 px | 1014.7 px | 510.5 – 520.0 px | 1023 px |

```
Preview comparison available at:
android/review/scale_alignment_comparison.png
```

### Jitter and Alignment Evaluation:
- **Frame-to-Frame Jitter:** Excellent. There are no sudden 1-frame accidental canvas shakes or jumps. Changes in `center_x` and `baseline` are smooth curves corresponding to intentional organic motion:
  - `idle`: Sub-pixel center stability (spread: 3.5 px, < 0.35% canvas width).
  - `thinking`: Character tilts head and leans torso rightward by up to 21 px (2.05% canvas width) at peak deliberation.
  - `sad`: Character slouches rightward by up to 20 px (1.95% canvas width).
  - `talk`: Perfectly centered horizontally (spread: 0.5 px).
- **Lower Baseline Consistency:**
  - `talk`, `happy`, `sad`, `surprised` have their feet/lower edge grounded at row `1023`.
  - `idle` sits slightly higher at `1016 – 1022` (delta is 1–7 px, < 0.7% canvas height).
  - The feet baseline across all states is well aligned.
- **Edge Clipping Risk:**
  - **Top Edge (row 0):** Touched by 7 frames in `idle`, 11 frames in `sad`, and 2 frames in `surprised`. Hair/head tips touch the canvas boundary.
  - **Bottom Edge (row 1023):** Touched by 10 frames in `thinking`, and **100% of frames** in `talk` (19/19), `happy` (16/16), `sad` (21/21), and `surprised` (23/23). The character is cropped flush with the bottom canvas.
- **Character Scale Discrepancy in `talk`:**
  - In `idle`, content height is **1015 px** and top starts at **y = 5 px**.
  - In `talk`, content height is **889 px** and top starts at **y = 134 px**.
  - Relative scale: `talk` character is **12.4% shorter** and **13.5% narrower** than `idle`.
  - **Visual impact:** When the assistant transitions from `IDLE` to `TALKING`, the character's head drops by 129 pixels and shrinks noticeably.

---

## 9. Duplicate and Suspicious-Frame Analysis

A full content-hash audit (SHA-256) revealed significant frame hold duplication:

```text
Total frames in package:     141
Globally unique frames:       84
Redundant duplicated frames:  57 (40.4% duplicate holds)
```

### 9.1 Intra-Action Hold Patterns
Many consecutive frames are byte-identical because the animator animated "on twos" or "on threes" (holding key poses):
- **`idle` (32 frames, 18 unique):**
  - Frames `0005`–`0006` hold 2 frames (`f86831c6`)
  - Frames `0007`–`0009` hold 3 frames (`3ef0cdb0`)
  - Frames `0010`–`0011` hold 2 frames (`34fda78d`)
  - Frames `0012`–`0013` hold 2 frames (`7a2b2201`)
  - Frames `0014`–`0015` hold 2 frames (`2114adfc`)
  - Frames `0019`–`0020` hold 2 frames (`34fda78d`)
  - Frames `0030`–`0032` hold 3 frames (`f86831c6`)
  - *Loop anchor:* Frame `0032` is identical to Frame `0001` (`f86831c6`).
- **`thinking` (30 frames, 18 unique):**
  - Baked ping-pong animation: Frames `0001`–`0016` animate forward, and frames `0017`–`0030` animate in reverse mirror.
  - *Loop anchor:* Frame `0030` is identical to Frame `0001` (`2f1af8d8`).
- **`talk` (19 frames, 18 unique):**
  - Fluid mouth cycle. Only 1 duplicate: Frame `0019` is identical to Frame `0001` (`08dd801a`) to anchor the loop.
- **`surprised` (23 frames, 7 unique):**
  - Extreme holds: Frames `0012`–`0016` hold the peak surprise expression for **5 consecutive frames** (`822215c8`). Frames `0017`–`0019` hold for 3 frames (`8b27037c`). Frames `0001`–`0002` and `0022`–`0023` hold the neutral resting pose (`9a02bda6`).

### 9.2 Suspicious Frame Glitch in `happy`
Analyzing the sequential hashes in `happy`:
- Frames `0001`–`0002`: Neutral rest (`9a02bda6`)
- Frames `0003`–`0006`: Entering smile
- Frame `0007`: Intermediate smile (`6c7f6300`)
- Frames `0009`–`0011`: Apex smile hold (`281ace08`)
- Frame `0012`: Returning intermediate smile (`6c7f6300`)
- Frames `0013`–`0015`: Neutral rest (`9a02bda6`)
- **Frame `0016` (ANOMALY):** Jumps back to `6c7f6300` (intermediate smile)!
  - *Finding:* Frame 16 was erroneously exported or appended. After resting at neutral (frames 13–15), frame 16 flashes a smile for 1 frame before ending.
  - *Correction:* Discard frame `0016` so `happy` terminates smoothly on neutral frame `0015`.

### 9.3 Cross-Action Identical Assets
Two hash groups are shared between `happy` and `surprised`:
1. `9a02bda6`: Shares the exact neutral rest frame across:
   - `happy`: `0001`, `0002`, `0013`, `0014`, `0015`
   - `surprised`: `0001`, `0002`, `0022`, `0023`
2. `6c7f6300`: Shares the intermediate smile pose across:
   - `happy`: `0007`, `0012`, `0016`
   - `surprised`: `0020`, `0021`

---

## 10. APK-Size and Decoded-Memory Estimates

### 10.1 Memory Calculation Formula
In Android, an uncompressed Bitmap loaded in standard `ARGB_8888` configuration consumes:
$$\text{Memory per Frame} = \text{Width} \times \text{Height} \times 4 \text{ bytes}$$
$$1024 \times 1024 \times 4 = 4,194,304 \text{ bytes} = 4.00 \text{ MB}$$

### 10.2 Simultaneous Decoded Memory Table

| Action | Frame Count | Decoded RAM per Frame | Action Total RAM | Compressed Disk Size |
|:---|:---:|:---:|:---:|:---:|
| `idle` | 32 | 4.00 MB | 128.00 MB | 17.98 MB |
| `thinking` | 30 | 4.00 MB | 120.00 MB | 12.93 MB |
| `talk` | 19 | 4.00 MB | 76.00 MB | 8.52 MB |
| `happy` | 16 | 4.00 MB | 64.00 MB | 9.21 MB |
| `sad` | 21 | 4.00 MB | 84.00 MB | 9.89 MB |
| `surprised` | 23 | 4.00 MB | 92.00 MB | 17.36 MB |
| **Full Package** | **141** | **4.00 MB** | **564.00 MB** | **75.89 MB** |

### 10.3 Risk Classification: `CRITICAL`
- **Standard Android Heap Limits:** Normal Android device app heap limits (`dalvik.vm.heapgrowthlimit`) range between **192 MB and 256 MB**.
- **Impact:**
  - Decoding the full package simultaneously requires **564 MB**, which exceeds standard process memory limits by over 200%, triggering an immediate `java.lang.OutOfMemoryError`.
  - Even loading a single action into memory at once (e.g., `idle` at 128 MB) consumes over 50% of the entire app heap, risking severe GC thrashing, frame drops, and background app kills.
- **APK Footprint:** Adding 75.89 MB directly into `res/drawable-nodpi/` inflates APK size by ~76 MB, which is unacceptable for mobile production distribution.

### 10.4 Target Canvas Recommendation
On target mobile devices, the character avatar is rendered inside an on-screen container of approximately `200.dp` to `280.dp`.
- At standard high-density `xhdpi` (2.0×), a 256.dp container requires a **512 × 512 px** image.
- At `xxhdpi` (3.0×), a 256.dp container requires a **768 × 768 px** image.
- **Recommendation:** Downscale master assets to **512 × 512 px**:
  - Memory per frame drops from **4.00 MB** to **1.00 MB** (75% RAM reduction).
  - `idle` total decoded memory drops to **32 MB**.
  - With WebP compression, compressed package drops from **75.89 MB** to **~4.5 MB**.

---

## 11. Recommended FPS and Playback Behavior

| Action | Total Frames | Unique Frames | Recommended FPS | Frame Duration | Cycle Duration | Playback Mode | End-State Behavior |
|:---|:---:|:---:|:---:|:---:|:---:|:---|:---|
| `idle` | 32 | 18 | **16 FPS** | 62.5 ms | ~2.00 s | Continuous Loop | Loop back to frame `0001` (seamless anchor). |
| `thinking` | 30 | 18 | **16 FPS** | 62.5 ms | ~1.88 s | Continuous Loop | Loop while waiting for server response. |
| `talk` | 19 | 18 | **18 FPS** | 55.5 ms | ~1.05 s | Continuous Loop | Loop continuously while TTS/audio is active. |
| `happy` | 15 *(pruned)* | 7 | **15 FPS** | 66.7 ms | ~1.00 s | One-Shot | Hold apex smile ~200ms; end on frame 15, return to `idle`. |
| `sad` | 21 | 18 | **14 FPS** | 71.4 ms | ~1.50 s | One-Shot | Plays once; upon completion, return to `idle`. |
| `surprised` | 23 | 7 | **16 FPS** | 62.5 ms | ~1.44 s | One-Shot | Apex surprise held for ~312ms; return to `idle`. |

### Playback Observations:
1. **No synthetic ping-pong required:** Both `idle` and `thinking` already contain forward-and-reverse frames in their sequence.
2. **Hold duration:** `surprised` and `happy` have intentional animator holds built directly into the frame sequence (e.g. 5 duplicate frames in `surprised` create a natural 312ms hold at 16 FPS).
3. **One-shot emotion completion:** Emotions should transition back to `idle` upon reaching their terminal frame.

---

## 12. Proposed Android Resource Naming

The current raw files are already named with standard resource conventions (`character_<action>_<0001..0032>.png`).  
To integrate directly into Android `res/drawable-nodpi/` or an asset folder without subdirectories:

### Naming Mapping:
- `idle/character_idle_0001.png` $\rightarrow$ `character_idle_0001.png`
- `thinking/character_thinking_0001.png` $\rightarrow$ `character_thinking_0001.png`
- `talk/character_talk_0001.png` $\rightarrow$ `character_talk_0001.png`
- `happy/character_happy_0001.png` $\rightarrow$ `character_happy_0001.png`
- `sad/character_sad_0001.png` $\rightarrow$ `character_sad_0001.png`
- `surprised/character_surprised_0001.png` $\rightarrow$ `character_surprised_0001.png`

### Code Domain Mapping Confirmation:
```kotlin
// Map state to asset prefix
val assetPrefix = when (state) {
    CharacterState.IDLE -> "character_idle"
    CharacterState.THINKING -> "character_thinking"
    CharacterState.TALKING -> when (emotion) {
        Emotion.NEUTRAL -> "character_talk"    // Mapped: folder 'talk' -> state TALKING
        Emotion.HAPPY -> "character_happy"
        Emotion.SAD -> "character_sad"
        Emotion.SURPRISED -> "character_surprised"
    }
}
```

---

## 13. Proposed Compose Integration Approach

### 13.1 Layered Full-Screen Layout
To satisfy the target design without keyboard interference:

```kotlin
Box(modifier = Modifier.fillMaxSize()) {
    // 1. Background layer
    CuteBackground(modifier = Modifier.fillMaxSize())

    // 2. Fixed Character Animation Layer (Behind Chat)
    // Anchored in upper/center area, independent of IME window insets
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .fillMaxHeight(0.6f)
            .align(Alignment.TopCenter),
        contentAlignment = Alignment.Center
    ) {
        CharacterAnimationPlayer(
            state = ui.characterState,
            emotion = ui.emotion,
            onEmotionFinished = vm::onEmotionAnimationComplete,
            modifier = Modifier.size(260.dp)
        )
    }

    // 3. Semi-transparent Chat Panel Layer (Lower ~50% of screen)
    Surface(
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.82f),
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        modifier = Modifier
            .fillMaxWidth()
            .fillMaxHeight(0.55f)
            .align(Alignment.BottomCenter)
            .consumeWindowInsets(PaddingValues(0.dp))
            .imePadding() // Only the chat surface responds to the keyboard!
    ) {
        // Chat LazyColumn and Input TextField
    }
}
```

### 13.2 Resource Strategy Tradeoff & Recommendation

#### Option 1: 141 Individual Drawables in `res/drawable-nodpi/`
- **Pros:** Native Android resource loading via `R.drawable.character_xxx`.
- **Cons:**
  - 141 individual XML / resource entries generated in `R.java`.
  - Massive APK size (~76 MB unless converted to WebP).
  - Main thread Bitmap decoding via `painterResource()` will trigger frame drops and potential OOMs if not carefully pooled.

#### Option 2: Pre-compiled Frame Arrays with In-Memory Double-Buffering (Recommended)
- **Implementation:**
  1. Downscale to **512 × 512** and convert to **lossless/high-quality WebP** in `res/drawable-nodpi/`.
  2. Define static immutable `IntArray` frame lists in code (no `getIdentifier()` reflection):
     ```kotlin
     val IDLE_FRAMES = intArrayOf(R.drawable.character_idle_0001, ...)
     val TALK_FRAMES = intArrayOf(R.drawable.character_talk_0001, ...)
     ```
  3. Drive playback with a `LaunchedEffect(state, emotion)` coroutine loop that advances an index at the specified frame interval.
  4. Reset frame index to `0` whenever `CharacterState` or `Emotion` transitions.
  5. For one-shot emotions (`happy`, `sad`, `surprised`), advance to the last frame and invoke `onEmotionFinished()`, resetting the state to `IDLE`.

---

## 14. Required Fixes Before Integration

The following issues must be resolved before assets are integrated into the Android repository:

### ISSUE-01: Extreme Memory Footprint & Canvas Oversizing
- **Severity:** `BLOCKER`
- **Affected:** All 141 files across all six actions.
- **Evidence:** Canvas is 1024 × 1024 px. Each frame = 4.00 MB uncompressed. Package simultaneous RAM = 564.00 MB. Total compressed disk size = 75.89 MB.
- **Impact:** Instant `OutOfMemoryError` on normal Android devices (heap growth limit ~192–256 MB), severe UI frame drops, and APK bloat.
- **Recommended Correction:** Downscale master assets to **512 × 512 px**. Convert PNGs to WebP.

### ISSUE-02: Character Scale & Position Misalignment in `talk`
- **Severity:** `HIGH`
- **Affected:** All 19 frames in `talk/`.
- **Evidence:** In `talk`, character bounding height is 889.5 px (vs 1015 px in `idle`), width is 510.1 px (vs 589.7 px in `idle`), and head top starts at y = 134 px (vs y = 5 px in `idle`).
- **Impact:** Switching between `idle` and `talk` causes the assistant to visibly shrink by ~13% and drop downwards.
- **Recommended Correction:** Have the artist re-render `talk` at the standard scale (~1015 px content height), or normalize and center the crop prior to production export.

### ISSUE-03: Animation Glitch in `happy` (Stray Frame 16)
- **Severity:** `HIGH`
- **Affected:** `happy/character_happy_0016.png`.
- **Evidence:** Frames `0013`–`0015` represent the neutral resting pose (`9a02bda6`), but frame `0016` unexpectedly jumps back to the intermediate smile pose (`6c7f6300`).
- **Impact:** At the end of the happy animation, the character pops back into a smile for 66 ms before resetting to idle.
- **Recommended Correction:** Discard frame `character_happy_0016.png` from the playback list so `happy` ends smoothly on frame `0015`.

### ISSUE-04: Mapping Discrepancy between Asset Folder and Legacy Code
- **Severity:** `HIGH`
- **Affected:** Action `talk` vs legacy code in `CharacterAvatar.kt`.
- **Evidence:** Asset folder is `talk`, producing `character_talk_xxxx.png`. Existing `CharacterAvatar.kt` hardcodes `characterAsset(CharacterState.TALKING, Emotion.NEUTRAL) = "talking"`.
- **Impact:** If unmapped, `TALKING` state fails to find resources.
- **Recommended Correction:** Update the mapping contract in the Compose integration layer to map `CharacterState.TALKING` directly to `character_talk`.

### ISSUE-05: Canvas Edge Touching / Clipping Risk
- **Severity:** `MEDIUM`
- **Affected:** 7 frames in `idle`, 11 in `sad`, 2 in `surprised` (top edge y=0); 10 frames in `thinking`, 100% of frames in `talk`, `happy`, `sad`, `surprised` (bottom edge y=1023).
- **Evidence:** Visible pixels touch `y = 0` and `y = 1023` without padding.
- **Impact:** Depending on anti-aliasing and viewport clipping in Compose, character hair and feet edges may exhibit harsh cutoff lines.
- **Recommended Correction:** Ensure at least 8–16 px of transparent padding around the character boundary during normalization.

---

## 15. Optional Improvements

1. **WebP Conversion:**  
   Convert normalized 512 × 512 PNGs to WebP (lossless or 95% quality). This reduces the package size from ~76 MB to under 5 MB with zero discernible visual quality loss.
2. **Hold De-duplication via Index Mapping:**  
   Because 57 of the 141 frames are duplicate holds, store only the 84 unique frames on disk and define the playback timing using an index map (e.g. `[1, 1, 2, 2, 3, 4, 5, 5, 5]`), saving an additional 40% in asset storage.
3. **Contact Sheet / Preview Artifacts:**  
   Preview sheets and scale comparisons have been generated and archived in `troLyAo_ani/android/review/` for visual inspection.

---

## 16. Files Created During the Audit

The following files were created during this audit:
1. `troLyAo_ani/android/tools/audit_character_frames.py` — Reusable, read-only Python inspection script.
2. `troLyAo_ani/android/review/audit_data.json` — Raw JSON metrics and bounding box data extracted during audit.
3. `troLyAo_ani/android/review/character_states_contact_sheet.png` — Contact sheet thumbnail overview of all six character states.
4. `troLyAo_ani/android/review/scale_alignment_comparison.png` — Visual comparison showing `idle` vs `talk` scale and baseline alignment.
5. `troLyAo_ani/android/review/character_frames_audit.md` — This comprehensive audit report.

---

## 17. Confirmation of Immutability

It is formally confirmed that:
- **Zero source images** in `character_frames_original/` were renamed, resized, compressed, moved, deleted, or edited.
- **Zero Android source files** or backend code files were modified.
- **Zero assets** were copied into `res/`.
- **Zero Git commits, branches, or pushes** were performed.
- **Zero new software packages** were installed in the environment.

---
*End of Audit Report.*
