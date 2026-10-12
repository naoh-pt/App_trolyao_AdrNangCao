package com.example.assistant.data.remote

import com.google.gson.annotations.SerializedName

data class ItemsResponse<T>(val items: List<T>)

data class ConversationDto(
    val id: String,
    val title: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
)

data class AssistantActionDto(
    val type: String,
    val label: String = "",
    val message: String? = null,
    @SerializedName("duration_seconds") val durationSeconds: Int? = null,
    val title: String? = null,
    @SerializedName("start_at") val startAt: String? = null,
    @SerializedName("end_at") val endAt: String? = null,
    val query: String? = null,
)

data class MessageDto(
    val id: String,
    val role: String,
    val text: String,
    val emotion: String?,
    @SerializedName("created_at") val createdAt: String,
    val action: AssistantActionDto? = null,
)

data class SendMessageRequest(
    @SerializedName("request_id") val requestId: String,
    val message: String,
)

data class SendMessageResponse(
    @SerializedName("user_message") val userMessage: MessageDto,
    @SerializedName("assistant_message") val assistantMessage: MessageDto,
    val action: AssistantActionDto? = null,
)

data class HealthResponse(val status: String?)

data class ErrorBody(val error: ErrorDetail?)
data class ErrorDetail(val code: String?, val message: String?)

class ApiException(
    val httpCode: Int?,
    val code: String?,
    override val message: String,
) : Exception(message)
