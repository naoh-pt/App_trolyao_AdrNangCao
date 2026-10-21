package com.example.assistant

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.ChatDisplaySettings
import com.example.assistant.domain.LocalAnimationFpsSettings
import com.example.assistant.domain.LocalChatDisplaySettings
import com.example.assistant.domain.LocalSpeechSettings
import com.example.assistant.domain.SpeechSettings
import com.example.assistant.speech.LocalTtsEnabled
import com.example.assistant.ui.chat.ChatScreen
import com.example.assistant.ui.chat.ChatViewModel
import com.example.assistant.ui.history.HistoryScreen
import com.example.assistant.ui.history.HistoryViewModel
import com.example.assistant.ui.home.HomeScreen
import com.example.assistant.ui.settings.SettingsScreen
import com.example.assistant.ui.settings.SettingsViewModel
import com.example.assistant.ui.memory.MemoryScreen
import com.example.assistant.ui.memory.MemoryViewModel
import com.example.assistant.ui.theme.AssistantTheme

object Routes {
    const val HOME = "home"
    const val HISTORY = "history"
    const val SETTINGS = "settings"
    const val MEMORY = "memory"
    const val CHAT = "chat/{id}"
    const val NEW = "new" // "chat mới": ChatViewModel tự tạo conversation_id trên server
    fun chat(id: String) = "chat/$id"
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val settingsStore = (application as AssistantApp).container.settings
        setContent {
            val fpsSettings by settingsStore.animationFpsSettings.collectAsStateWithLifecycle(
                initialValue = AnimationFpsSettings.DEFAULT,
            )
            val speechSettings by settingsStore.speechSettings.collectAsStateWithLifecycle(
                initialValue = SpeechSettings.DEFAULT,
            )
            val chatDisplaySettings by settingsStore.chatDisplaySettings.collectAsStateWithLifecycle(
                initialValue = ChatDisplaySettings.DEFAULT,
            )
            CompositionLocalProvider(
                LocalAnimationFpsSettings provides fpsSettings,
                LocalSpeechSettings provides speechSettings,
                LocalTtsEnabled provides speechSettings.enabled,
                LocalChatDisplaySettings provides chatDisplaySettings,
            ) {
                AssistantTheme { AppNav() }
            }
        }
    }
}

@Composable
fun AppNav() {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = Routes.HOME) {
        composable(Routes.HOME) {
            HomeScreen(
                onStartChat = { nav.navigate(Routes.chat(Routes.NEW)) },
                onHistory = { nav.navigate(Routes.HISTORY) },
                onSettings = { nav.navigate(Routes.SETTINGS) },
            )
        }
        composable(
            route = Routes.CHAT,
            arguments = listOf(navArgument("id") { type = NavType.StringType }),
        ) { entry ->
            val id = entry.arguments?.getString("id")
            val vm: ChatViewModel = viewModel(
                factory = ChatViewModel.factory(if (id == null || id == Routes.NEW) null else id),
            )
            ChatScreen(
                vm = vm,
                onBack = { nav.popBackStack() },
                // Về History nhưng Back từ History vẫn quay về Home.
                onHistory = { nav.navigate(Routes.HISTORY) { popUpTo(Routes.HOME) } },
            )
        }
        composable(Routes.HISTORY) {
            val vm: HistoryViewModel = viewModel(factory = HistoryViewModel.Factory)
            HistoryScreen(
                vm = vm,
                onBack = { nav.popBackStack() },
                onOpenChat = { nav.navigate(Routes.chat(it)) },
            )
        }
        composable(Routes.SETTINGS) {
            val vm: SettingsViewModel = viewModel(factory = SettingsViewModel.Factory)
            SettingsScreen(vm = vm, onBack = { nav.popBackStack() }, onMemory = { nav.navigate(Routes.MEMORY) })
        }
        composable(Routes.MEMORY) {
            val vm: MemoryViewModel = viewModel(factory = MemoryViewModel.Factory)
            MemoryScreen(vm = vm, onBack = { nav.popBackStack() })
        }
    }
}
