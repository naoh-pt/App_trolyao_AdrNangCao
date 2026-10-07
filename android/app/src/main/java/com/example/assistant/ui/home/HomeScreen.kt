package com.example.assistant.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import com.example.assistant.ui.components.CharacterAvatar
import com.example.assistant.ui.components.CuteBackground

@Composable
fun HomeScreen(onStartChat: () -> Unit, onHistory: () -> Unit, onSettings: () -> Unit) {
    CuteBackground {
        Column(
            modifier = Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            CharacterAvatar(
                state = CharacterState.IDLE,
                emotion = Emotion.NEUTRAL,
                modifier = Modifier.fillMaxWidth().height(280.dp),
            )
            Spacer(Modifier.height(16.dp))
            Text(
                "Trợ lý ảo ✨",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                "Xin chào! Mình sẵn sàng trò chuyện cùng bạn nè~",
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 4.dp),
            )
            Spacer(Modifier.height(28.dp))
            Button(
                onClick = onStartChat,
                shape = CircleShape,
                modifier = Modifier.fillMaxWidth().height(54.dp),
            ) { Text("💬  Bắt đầu trò chuyện", fontWeight = FontWeight.Bold) }
            Spacer(Modifier.height(12.dp))
            OutlinedButton(
                onClick = onHistory,
                shape = CircleShape,
                modifier = Modifier.fillMaxWidth().height(50.dp),
            ) { Text("🕘  Lịch sử") }
            Spacer(Modifier.height(10.dp))
            OutlinedButton(
                onClick = onSettings,
                shape = CircleShape,
                modifier = Modifier.fillMaxWidth().height(50.dp),
            ) { Text("⚙️  Cài đặt") }
        }
    }
}
