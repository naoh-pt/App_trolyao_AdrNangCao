package com.example.assistant.data.remote

import com.google.gson.annotations.SerializedName

data class ItemsResponse<T>(val items: List<T>)

data class ConversationDto(
    val id: String,
    val title: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
)

data class MessageDto(
    val id: String,
    val role: String,
    val text: String,
    val emotion: String?,
    @SerializedName("created_at") val createdAt: String,
)

data class SendMessageRequest(
    @SerializedName("request_id") val requestId: String,
    val message: String,
)

data class SendMessageResponse(
    @SerializedName("user_message") val userMessage: MessageDto,
    @SerializedName("assistant_message") val assistantMessage: MessageDto,
)

data class HealthResponse(val status: String?)

data class ErrorBody(val error: ErrorDetail?)
data class ErrorDetail(val code: String?, val message: String?)

class ApiException(
    val httpCode: Int?,
    val code: String?,
    override val message: String,
) : Exception(message)
