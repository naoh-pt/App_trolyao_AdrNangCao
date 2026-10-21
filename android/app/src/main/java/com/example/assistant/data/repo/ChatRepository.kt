package com.example.assistant.data.repo

import androidx.room.withTransaction
import com.example.assistant.data.local.AppDatabase
import com.example.assistant.data.local.ConversationEntity
import com.example.assistant.data.local.MessageEntity
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.data.remote.ApiClient
import com.example.assistant.data.remote.ApiException
import com.example.assistant.data.remote.ChatApi
import com.example.assistant.data.remote.ConversationDto
import com.example.assistant.data.remote.ErrorBody
import com.example.assistant.data.remote.MessageDto
import com.example.assistant.data.remote.MemoryDto
import com.example.assistant.domain.CompanionPreferences
import com.example.assistant.data.remote.SendMessageRequest
import com.google.gson.Gson
import com.google.gson.JsonParseException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import retrofit2.Response
import java.io.IOException
import java.time.Instant

data class AssistantReply(
    val message: MessageEntity,
    val action: com.example.assistant.data.remote.AssistantActionDto? = null,
)

/**
 * Nguồn dữ liệu chính là backend; Room chỉ là cache để xem khi offline.
 * Mọi hàm public trả về Result, lỗi là ApiException có message tiếng Việt để hiện thẳng lên UI.
 */
class ChatRepository(
    private val db: AppDatabase,
    private val apiClient: ApiClient,
    private val settings: SettingsStore,
) : MemoryGateway, CompanionGateway {
    private val convDao = db.conversationDao()
    private val msgDao = db.messageDao()
    private val gson = Gson()

    fun observeConversations(): Flow<List<ConversationEntity>> = convDao.observeAll()
    fun observeMessages(conversationId: String): Flow<List<MessageEntity>> = msgDao.observe(conversationId)

    override suspend fun ownerId(): String = settings.clientId()

    override suspend fun getCompanion(owner: String): Result<CompanionPreferences> = safe {
        call { api, cid ->
            check(cid == owner)
            api.companion(cid)
        }.also { check(it.valid()) }
    }

    override suspend fun saveCompanion(owner: String, preferences: CompanionPreferences): Result<CompanionPreferences> = safe {
        check(preferences.valid())
        call { api, cid ->
            check(cid == owner)
            api.saveCompanion(cid, preferences)
        }.also { check(it.valid()) }
    }

    suspend fun claimMoodDate(owner: String, date: String): Boolean = settings.claimMoodDate(owner, date)

    override suspend fun listMemories(): Result<List<MemoryDto>> = safe {
        call { api, cid -> api.memories(cid) }.items
    }

    override suspend fun deleteMemory(id: String): Result<Unit> = safe {
        call { api, cid -> api.deleteMemory(id, cid) }
    }

    suspend fun checkIn(id: String): Result<MessageDto?> = safe {
        call { api, cid -> api.checkIn(id, cid) }.message
    }

    suspend fun cacheCheckIn(id: String, message: MessageDto) {
        if (message.role == "assistant") msgDao.upsertAll(listOf(message.toEntity(id)))
    }

    suspend fun checkHealth(baseUrl: String? = null): Result<Unit> = safe {
        val r = call(baseUrl) { api, _ -> api.health() }
        if (r.status != "ok") throw ApiException(null, "BAD_HEALTH", "Server phản hồi không đúng (status != ok)")
    }

    suspend fun refreshConversations(): Result<Unit> = safe {
        val items = call { api, cid -> api.conversations(cid) }.items
        db.withTransaction {
            if (items.isEmpty()) {
                convDao.deleteAll()
            } else {
                convDao.deleteNotIn(items.map { it.id })
                convDao.upsertAll(items.map { it.toEntity() })
            }
        }
    }

    suspend fun refreshMessages(conversationId: String): Result<Unit> = safe {
        val items = call { api, cid -> api.messages(conversationId, cid) }.items
        db.withTransaction {
            if (items.isEmpty()) {
                msgDao.deleteByConversation(conversationId)
            } else {
                msgDao.deleteNotIn(conversationId, items.map { it.id })
                msgDao.upsertAll(items.map { it.toEntity(conversationId) })
            }
        }
    }

    suspend fun createConversation(): Result<ConversationEntity> = safe {
        val dto = call { api, cid -> api.createConversation(cid, emptyMap()) }
        dto.toEntity().also { convDao.upsert(it) }
    }

    suspend fun deleteConversation(id: String): Result<Unit> = safe {
        try {
            call { api, cid -> api.deleteConversation(id, cid) }
        } catch (e: ApiException) {
            if (e.httpCode != 404) throw e // 404 = server không còn chat này -> xóa cache luôn
        }
        db.withTransaction {
            msgDao.deleteByConversation(id)
            convDao.deleteById(id)
        }
    }


    /** Dùng lại cùng requestId khi thử lại để backend không tạo tin nhắn kép. Trả về tin nhắn của trợ lý và hành động đính kèm (nếu có). */
    suspend fun sendMessage(
        conversationId: String,
        requestId: String,
        text: String,
        beforeAssistantCached: (MessageEntity) -> Unit = {},
    ): Result<AssistantReply> = safe {
        val resp = call { api, cid -> api.sendMessage(conversationId, cid, SendMessageRequest(requestId, text)) }
        val user = resp.userMessage.toEntity(conversationId)
        val bot = resp.assistantMessage.toEntity(conversationId)
        // Let presentation mask this exact row before Room can publish the complete text.
        // Persistence still always receives the complete, unchanged response.
        beforeAssistantCached(bot)
        msgDao.upsertAll(listOf(user, bot))
        refreshConversations() // cập nhật tiêu đề / updated_at, lỗi cũng bỏ qua
        val action = resp.action ?: resp.assistantMessage.action
        AssistantReply(message = bot, action = action)
    }

    // ---------- nội bộ ----------

    private suspend fun <T> call(baseUrl: String? = null, block: suspend (ChatApi, String) -> Response<T>): T {
        val rawUrl = baseUrl ?: settings.baseUrl.first()
        val url = SettingsStore.normalize(rawUrl)
            ?: throw ApiException(null, "BAD_URL", "Địa chỉ backend không hợp lệ")
        val clientId = settings.clientId()
        val api = try {
            apiClient.forBase(url)
        } catch (e: IllegalArgumentException) {
            throw ApiException(null, "BAD_URL", "Địa chỉ backend không hợp lệ")
        }
        val resp = try {
            block(api, clientId)
        } catch (e: CancellationException) {
            throw e
        } catch (e: java.net.SocketTimeoutException) {
            throw ApiException(null, "NETWORK", "Hết thời gian chờ phản hồi từ server (timeout)")
        } catch (e: java.net.ConnectException) {
            throw ApiException(null, "NETWORK", "Không thể kết nối tới server (Connection refused). Kiểm tra xem backend đã chạy chưa.")
        } catch (e: java.net.UnknownHostException) {
            throw ApiException(null, "NETWORK", "Không tìm thấy địa chỉ server. Kiểm tra kết nối mạng hoặc IP backend.")
        } catch (e: IOException) {
            throw ApiException(null, "NETWORK", "Không kết nối được tới server. Kiểm tra Wi-Fi và địa chỉ backend.")
        } catch (e: JsonParseException) {
            throw ApiException(null, "BAD_RESPONSE", "Phản hồi của server không đúng định dạng")
        }

        if (resp.isSuccessful) {
            val body = resp.body()
            if (body != null) return body
            @Suppress("UNCHECKED_CAST")
            if (resp.code() == 204 || resp.code() == 205) return Unit as T
            try {
                @Suppress("UNCHECKED_CAST")
                return Unit as T
            } catch (_: Exception) {
                throw ApiException(resp.code(), "EMPTY_BODY", "Phản hồi của server rỗng")
            }
        }

        val raw = resp.errorBody()?.string()
        val parsed = runCatching { gson.fromJson(raw, ErrorBody::class.java) }.getOrNull()
        val message = parsed?.error?.message ?: when (resp.code()) {
            400 -> "Nội dung yêu cầu không hợp lệ (HTTP 400)"
            404 -> "Không tìm thấy tài nguyên yêu cầu (HTTP 404)"
            409 -> "Xung đột dữ liệu (HTTP 409)"
            422 -> "Dữ liệu gửi lên không đúng định dạng (HTTP 422)"
            500 -> "Lỗi hệ thống server (HTTP 500)"
            503 -> "Không thể kết nối dịch vụ AI (HTTP 503)"
            504 -> "Dịch vụ AI phản hồi quá chậm (HTTP 504)"
            else -> "Lỗi server (${resp.code()})"
        }
        throw ApiException(resp.code(), parsed?.error?.code, message)
    }

    private suspend fun <T> safe(block: suspend () -> T): Result<T> = try {
        Result.success(block())
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        Result.failure(e)
    }

    private fun millis(iso: String): Long = runCatching { Instant.parse(iso).toEpochMilli() }.getOrDefault(0L)

    private fun ConversationDto.toEntity() =
        ConversationEntity(id, title, millis(createdAt), millis(updatedAt))

    private fun MessageDto.toEntity(conversationId: String) =
        MessageEntity(id, conversationId, role, text, emotion, millis(createdAt))
}
