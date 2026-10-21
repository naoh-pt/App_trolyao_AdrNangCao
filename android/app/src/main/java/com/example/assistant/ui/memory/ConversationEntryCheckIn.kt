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
    private val onOutcome: suspend (Boolean?) -> Unit = {},
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
                val result = load(id)
                if (currentId != id || generation != token) return@launch
                if (result.isFailure) { onOutcome(null); return@launch }
                val message = result.getOrNull()
                if (message == null) { onOutcome(false); return@launch }
                if (message.role != "assistant") return@launch
                if (delivered.add(message.id)) cache(id, message)
                if (currentId == id && generation == token) onOutcome(true)
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
