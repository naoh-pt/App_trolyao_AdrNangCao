package com.example.assistant.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/** Nền gradient pastel xanh → hồng → trắng với vài đốm sáng tròn mờ. */
@Composable
fun CuteBackground(modifier: Modifier = Modifier, content: @Composable BoxScope.() -> Unit) {
    Box(
        modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFFD9ECFF), Color(0xFFFFEEF5), Color.White)))
            .drawBehind {
                drawCircle(Color.White.copy(alpha = 0.55f), size.width * 0.28f, Offset(size.width * 0.9f, size.height * 0.12f))
                drawCircle(Color(0xFFFFC2DA).copy(alpha = 0.25f), size.width * 0.22f, Offset(size.width * 0.05f, size.height * 0.45f))
                drawCircle(Color(0xFFB9DCFF).copy(alpha = 0.30f), size.width * 0.30f, Offset(size.width * 0.85f, size.height * 0.85f))
            },
    ) { content() }
}
