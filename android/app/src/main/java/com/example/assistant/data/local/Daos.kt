package com.example.assistant.data.local

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface ConversationDao {
    @Query("SELECT * FROM conversations ORDER BY updatedAt DESC")
    fun observeAll(): Flow<List<ConversationEntity>>

    @Upsert
    suspend fun upsertAll(items: List<ConversationEntity>)

    @Upsert
    suspend fun upsert(item: ConversationEntity)

    @Query("DELETE FROM conversations WHERE id NOT IN (:keepIds)")
    suspend fun deleteNotIn(keepIds: List<String>)

    @Query("DELETE FROM conversations")
    suspend fun deleteAll()

    @Query("DELETE FROM conversations WHERE id = :id")
    suspend fun deleteById(id: String)
}

@Dao
interface MessageDao {
    @Query("SELECT * FROM messages WHERE conversationId = :conversationId ORDER BY createdAt ASC, CASE WHEN role = 'user' THEN 0 ELSE 1 END ASC, id ASC")
    fun observe(conversationId: String): Flow<List<MessageEntity>>

    @Upsert
    suspend fun upsertAll(items: List<MessageEntity>)

    @Query("DELETE FROM messages WHERE conversationId = :conversationId AND id NOT IN (:keepIds)")
    suspend fun deleteNotIn(conversationId: String, keepIds: List<String>)

    @Query("DELETE FROM messages WHERE conversationId = :conversationId")
    suspend fun deleteByConversation(conversationId: String)
}
