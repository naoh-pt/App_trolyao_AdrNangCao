package com.example.assistant.data.repo

import com.example.assistant.data.remote.MemoryDto

interface MemoryGateway {
    suspend fun listMemories(): Result<List<MemoryDto>>
    suspend fun deleteMemory(id: String): Result<Unit>
}
