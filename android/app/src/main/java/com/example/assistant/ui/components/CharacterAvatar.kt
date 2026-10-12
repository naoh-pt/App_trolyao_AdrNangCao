package com.example.assistant.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import com.example.assistant.domain.LocalAnimationFpsSettings
import com.example.assistant.ui.character.CharacterAnimationPlayer
import com.example.assistant.ui.character.animationSpecFor

/**
 * Character avatar component.
 *
 * Resolves the appropriate animation specification from [state] and [emotion] using
 * [animationSpecFor], applies effective FPS from [fpsSettings], and delegates rendering
 * to [CharacterAnimationPlayer].
 *
 * Preserves stable layout bounds, centers the character horizontally, and anchors it to the bottom
 * without artificial bounce transitions or dynamic reflection lookups.
 *
 * @param state Active high-level character state (IDLE, THINKING, TALKING).
 * @param emotion Active emotion (NEUTRAL, HAPPY, SAD, SURPRISED).
 * @param modifier Caller-provided layout modifier.
 * @param fpsSettings Effective FPS settings (defaults to [LocalAnimationFpsSettings.current]).
 * @param restartKey Optional key whose change explicitly restarts the animation.
 * @param onOneShotFinished Optional callback invoked upon completion of a one-shot animation.
 */
@Composable
fun CharacterAvatar(
    state: CharacterState,
    emotion: Emotion,
    modifier: Modifier = Modifier,
    fpsSettings: AnimationFpsSettings = LocalAnimationFpsSettings.current,
    restartKey: Any? = null,
    onOneShotFinished: () -> Unit = {},
) {
    val baseSpec = animationSpecFor(state, emotion)
    val effectiveSpec = fpsSettings.applyOverride(baseSpec)
    Box(
        modifier = modifier,
        contentAlignment = Alignment.BottomCenter,
    ) {
        CharacterAnimationPlayer(
            spec = effectiveSpec,
            modifier = Modifier.fillMaxSize(),
            contentDescription = null,
            restartKey = restartKey,
            onOneShotFinished = onOneShotFinished,
        )
    }
}
