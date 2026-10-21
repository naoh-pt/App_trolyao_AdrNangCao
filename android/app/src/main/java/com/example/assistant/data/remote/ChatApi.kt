package com.example.assistant.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Hợp đồng API MVP. Mọi path có prefix "api/v1/" — nếu nhóm quyết định /health nằm ngoài prefix,
 * chỉ cần sửa dòng @GET của health().
 */
interface ChatApi {
    @GET("api/v1/memories")
    suspend fun memories(@Header("X-Client-Id") clientId: String): Response<ItemsResponse<MemoryDto>>

    @DELETE("api/v1/memories/{id}")
    suspend fun deleteMemory(@Path("id") id: String, @Header("X-Client-Id") clientId: String): Response<Unit>

    @POST("api/v1/conversations/{id}/check-in")
    suspend fun checkIn(@Path("id") id: String, @Header("X-Client-Id") clientId: String): Response<CheckInResponse>

    @GET("api/v1/health")
    suspend fun health(): Response<HealthResponse>

    @POST("api/v1/conversations")
    suspend fun createConversation(
        @Header("X-Client-Id") clientId: String,
        @Body body: Map<String, String>,
    ): Response<ConversationDto>

    @GET("api/v1/conversations")
    suspend fun conversations(
        @Header("X-Client-Id") clientId: String,
    ): Response<ItemsResponse<ConversationDto>>

    @GET("api/v1/conversations/{id}/messages")
    suspend fun messages(
        @Path("id") id: String,
        @Header("X-Client-Id") clientId: String,
    ): Response<ItemsResponse<MessageDto>>

    @DELETE("api/v1/conversations/{id}")
    suspend fun deleteConversation(
        @Path("id") id: String,
        @Header("X-Client-Id") clientId: String,
    ): Response<Unit>

    @POST("api/v1/conversations/{id}/messages")
    suspend fun sendMessage(
        @Path("id") id: String,
        @Header("X-Client-Id") clientId: String,
        @Body body: SendMessageRequest,
    ): Response<SendMessageResponse>
}
