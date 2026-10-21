package com.example.assistant.data.repo

import com.example.assistant.domain.CompanionPreferences

interface CompanionGateway {
    suspend fun ownerId(): String
    suspend fun getCompanion(owner: String): Result<CompanionPreferences>
    suspend fun saveCompanion(owner: String, preferences: CompanionPreferences): Result<CompanionPreferences>
}
