package com.example.assistant.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

// Bảng màu pastel: xanh lam (chủ đạo, khớp nhân vật của B) + hồng phấn làm điểm nhấn.
private val Colors = lightColorScheme(
    primary = Color(0xFF4A9BEA),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFCFE6FF),
    onPrimaryContainer = Color(0xFF14325C),
    secondary = Color(0xFFFF8FB8),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFFFE0EC),
    onSecondaryContainer = Color(0xFF5A1735),
    background = Color(0xFFF4F9FF),
    surface = Color.White,
    surfaceVariant = Color(0xFFFFF4F8),
    errorContainer = Color(0xFFFFE3E8),
)

private val CuteShapes = Shapes(
    extraSmall = RoundedCornerShape(12.dp),
    small = RoundedCornerShape(16.dp),
    medium = RoundedCornerShape(24.dp),
    large = RoundedCornerShape(32.dp),
    extraLarge = RoundedCornerShape(40.dp),
)

@Composable
fun AssistantTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, shapes = CuteShapes, content = content)
}
