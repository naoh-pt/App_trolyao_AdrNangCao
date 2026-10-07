package com.example.assistant

import android.app.Application
import android.content.Context
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.room.Room
import com.example.assistant.data.local.AppDatabase
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.data.remote.ApiClient
import com.example.assistant.data.repo.ChatRepository

class AppContainer(context: Context) {
    val settings = SettingsStore(context)
    private val db = Room.databaseBuilder(context, AppDatabase::class.java, "assistant.db").build()
    val repository = ChatRepository(db, ApiClient(), settings)
}

class AssistantApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}

fun CreationExtras.assistantApp(): AssistantApp =
    this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as AssistantApp
