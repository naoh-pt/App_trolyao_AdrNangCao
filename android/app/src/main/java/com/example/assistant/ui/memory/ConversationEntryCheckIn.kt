package com.example.assistant.ui.memory

import com.example.assistant.data.remote.MessageDto
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/** Owned by the existing chat ViewModel: no lifecycle polling or Compose effects. */
class ConversationEntryCheckIn(
    private val scope: CoroutineScope,
    private val load: suspend (String) -> Result<MessageDto?>,
    private val cache: suspend (String, MessageDto) -> Unit,
) {
    private var currentId: String? = null
    private var generation = 0
    private var job: Job? = null
    private val delivered = mutableSetOf<String>()

    fun enter(id: String?) {
        if (id == null || id == currentId) return
        job?.cancel()
        currentId = id
        val token = ++generation
        job = scope.launch {
            try {
                val message = load(id).getOrNull() ?: return@launch
                if (currentId != id || generation != token || message.role != "assistant") return@launch
                if (delivered.add(message.id)) cache(id, message)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                // Optional entry check-in never blocks chat; persisted history can recover it.
            }
        }
    }

    fun leave() {
        currentId = null
        generation++
        job?.cancel()
    }
}
