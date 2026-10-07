package com.example.assistant.ui.character

import androidx.compose.foundation.Image
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.isActive

/**
 * Pure mapping function resolving a [CharacterAnimationSpec] from [CharacterState] and [Emotion].
 *
 * Current Stage 2 mapping preserves direct behavior:
 * - IDLE                -> idle (loop)
 * - THINKING            -> thinking (loop)
 * - TALKING + NEUTRAL   -> talk (loop)
 * - TALKING + HAPPY     -> happy (one-shot)
 * - TALKING + SAD       -> sad (one-shot)
 * - TALKING + SURPRISED -> surprised (one-shot)
 */
fun animationSpecFor(
    state: CharacterState,
    emotion: Emotion,
): CharacterAnimationSpec = when (state) {
    CharacterState.IDLE -> CharacterFrameCatalog.idle
    CharacterState.THINKING -> CharacterFrameCatalog.thinking
    CharacterState.TALKING -> when (emotion) {
        Emotion.NEUTRAL -> CharacterFrameCatalog.talk
        Emotion.HAPPY -> CharacterFrameCatalog.happy
        Emotion.SAD -> CharacterFrameCatalog.sad
        Emotion.SURPRISED -> CharacterFrameCatalog.surprised
    }
}

/**
 * Pure calculation function determining the active frame index based on elapsed playback time.
 *
 * Requirements:
 * - Never returns a negative value.
 * - Never returns an index outside [spec.frames.indices].
 * - Looping animations wrap via modulo.
 * - One-shot animations stop at the final frame.
 * - Empty frame arrays return 0 safely.
 * - Negative elapsed time behaves as 0.
 */
fun frameIndexForElapsed(
    elapsedMs: Long,
    spec: CharacterAnimationSpec,
): Int {
    val frameCount = spec.frames.size
    if (frameCount == 0) return 0
    if (elapsedMs <= 0L) return 0

    val frameDuration = spec.frameDurationMs
    if (frameDuration <= 0L) return 0

    val frameSteps = elapsedMs / frameDuration
    return when (spec.mode) {
        PlaybackMode.LOOP -> (frameSteps % frameCount).toInt()
        PlaybackMode.ONE_SHOT -> minOf(frameSteps, (frameCount - 1).toLong()).toInt()
    }
}

/**
 * Pure function determining whether a one-shot animation has reached or exceeded its total duration.
 * Looping animations and empty frame arrays never finish.
 */
fun isAnimationFinished(
    elapsedMs: Long,
    spec: CharacterAnimationSpec,
): Boolean {
    if (spec.isLooping || spec.frames.isEmpty()) return false
    val effectiveElapsed = if (elapsedMs < 0L) 0L else elapsedMs
    return effectiveElapsed >= spec.totalDurationMs
}

/**
 * Standalone character animation player composable.
 *
 * Renders individual frames driven by a frame clock ([withFrameNanos]), respecting lifecycle state
 * ([Lifecycle.State.STARTED]). Keeps layout bounds stable and displays only the current drawable
 * without preloading or caching lists of Bitmaps/Painters.
 *
 * @param spec Animation specification containing frames, fps, and playback mode.
 * @param modifier Modifier applied to the rendered image.
 * @param contentDescription Optional accessibility description (defaults to null for decorative character).
 * @param onOneShotFinished Callback invoked exactly once upon completion of a one-shot animation.
 */
@Composable
fun CharacterAnimationPlayer(
    spec: CharacterAnimationSpec,
    modifier: Modifier = Modifier,
    contentDescription: String? = null,
    onOneShotFinished: () -> Unit = {},
) {
    val currentOnFinished by rememberUpdatedState(onOneShotFinished)
    val lifecycleOwner = LocalLifecycleOwner.current

    var currentFrameIndex by remember(spec) { mutableIntStateOf(0) }

    LaunchedEffect(spec, lifecycleOwner) {
        if (spec.frames.isEmpty()) return@LaunchedEffect

        var accumulatedElapsedNanos = 0L
        var hasNotifiedCompletion = false

        lifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            // If already completed one-shot before pause, stay on last frame and suspend
            if (!spec.isLooping && isAnimationFinished(accumulatedElapsedNanos / 1_000_000L, spec)) {
                currentFrameIndex = spec.frames.size - 1
                awaitCancellation()
            }

            var lastFrameNanos = withFrameNanos { it }

            while (isActive) {
                withFrameNanos { nowNanos ->
                    val deltaNanos = nowNanos - lastFrameNanos
                    lastFrameNanos = nowNanos
                    accumulatedElapsedNanos += deltaNanos

                    val elapsedMs = accumulatedElapsedNanos / 1_000_000L
                    val newIndex = frameIndexForElapsed(elapsedMs, spec)
                    currentFrameIndex = newIndex

                    if (!spec.isLooping && isAnimationFinished(elapsedMs, spec)) {
                        if (!hasNotifiedCompletion) {
                            hasNotifiedCompletion = true
                            currentOnFinished()
                        }
                    }
                }

                if (!spec.isLooping && hasNotifiedCompletion) {
                    awaitCancellation()
                }
            }
        }
    }

    val currentResId = if (spec.frames.isNotEmpty()) {
        spec.frames[currentFrameIndex]
    } else {
        0
    }

    if (currentResId != 0) {
        Image(
            painter = painterResource(currentResId),
            contentDescription = contentDescription,
            modifier = modifier,
            contentScale = ContentScale.Fit,
            alignment = Alignment.BottomCenter,
        )
    }
}
