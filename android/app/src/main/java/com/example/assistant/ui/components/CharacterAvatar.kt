package com.example.assistant.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion

/** Tên asset theo quy chuẩn character_<tên>.png. NEUTRAL dùng ảnh idle. */
fun characterAsset(state: CharacterState, emotion: Emotion): String = when (state) {
    CharacterState.IDLE -> "idle"
    CharacterState.THINKING -> "thinking"
    CharacterState.TALKING -> when (emotion) {
        Emotion.NEUTRAL -> "talking"
        Emotion.HAPPY -> "happy"
        Emotion.SAD -> "sad"
        Emotion.SURPRISED -> "surprised"
    }
}

private fun placeholderEmoji(asset: String) = when (asset) {
    "thinking" -> "🤔"
    "talking" -> "💬"
    "happy" -> "😊"
    "sad" -> "😢"
    "surprised" -> "😮"
    else -> "🙂"
}

/** Màu quầng sáng phía sau nhân vật đổi theo tâm trạng. */
private fun glowColor(asset: String) = when (asset) {
    "happy" -> Color(0xFFFFD6E8)
    "sad" -> Color(0xFFC9D9F5)
    "surprised" -> Color(0xFFFFF0B8)
    "thinking" -> Color(0xFFE4D9FF)
    else -> Color(0xFFCFE6FF)
}

@Composable
fun CharacterAvatar(state: CharacterState, emotion: Emotion, modifier: Modifier = Modifier) {
    val asset = characterAsset(state, emotion)
    val context = LocalContext.current
    // Chưa có PNG của B -> resId = 0 -> hiện emoji tạm, app vẫn chạy được.
    val resId = remember(asset) {
        context.resources.getIdentifier("character_$asset", "drawable", context.packageName)
    }
    val talking = state == CharacterState.TALKING
    val transition = rememberInfiniteTransition(label = "character")
    // Nhân vật luôn "bồng bềnh" nhẹ; nhún nhanh hơn khi đang nói.
    val bounce by transition.animateFloat(
        initialValue = 0f,
        targetValue = if (talking) -16f else -8f,
        animationSpec = infiniteRepeatable(
            tween(if (talking) 350 else 1600, easing = FastOutSlowInEasing),
            RepeatMode.Reverse,
        ),
        label = "bounce",
    )

    BoxWithConstraints(modifier, contentAlignment = Alignment.Center) {
        val side = minOf(maxHeight, maxWidth) * 0.92f
        Box(
            Modifier.size(side).graphicsLayer { translationY = bounce },
            contentAlignment = Alignment.Center,
        ) {
            Box(
                Modifier
                    .fillMaxSize()
                    .shadow(8.dp, CircleShape)
                    .clip(CircleShape)
                    .background(Brush.radialGradient(listOf(Color.White, glowColor(asset)))),
            )
            if (resId != 0) {
                Image(
                    painter = painterResource(resId),
                    contentDescription = "Nhân vật trợ lý ($asset)",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit,
                )
            } else {
                Text(placeholderEmoji(asset), fontSize = (side.value * 0.5f).sp)
            }
        }
    }
}
