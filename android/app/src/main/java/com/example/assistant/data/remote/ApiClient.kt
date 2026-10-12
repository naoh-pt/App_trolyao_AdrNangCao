package com.example.assistant.data.remote

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/** Tạo (và cache) Retrofit theo địa chỉ backend hiện tại; đổi IP trong Cài đặt là có hiệu lực ngay. */
class ApiClient {
    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .readTimeout(65, TimeUnit.SECONDS) // backend timeout budget tối đa 52s-55s
        .build()

    private var cachedUrl: String? = null
    private var cachedApi: ChatApi? = null

    @Synchronized
    fun forBase(baseUrl: String): ChatApi {
        val normalized = com.example.assistant.data.local.SettingsStore.normalize(baseUrl)
            ?: throw IllegalArgumentException("Địa chỉ backend không hợp lệ: $baseUrl")
        val cached = cachedApi
        if (cached != null && cachedUrl == normalized) return cached
        val api = Retrofit.Builder()
            .baseUrl(normalized)
            .client(http)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ChatApi::class.java)
        cachedUrl = normalized
        cachedApi = api
        return api
    }
}
