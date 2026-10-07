package com.example.assistant

import com.example.assistant.data.local.MessageEntity
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.domain.Emotion
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import java.util.UUID

class UnitTest {

    @Test
    fun testBaseUrlNormalization() {
        assertEquals("http://192.168.137.1:8000/", SettingsStore.normalize("192.168.137.1:8000"))
        assertEquals("http://192.168.137.1:8000/", SettingsStore.normalize("http://192.168.137.1:8000/"))
        assertEquals("http://192.168.137.1:8000/", SettingsStore.normalize("http://192.168.137.1:8000/api/v1"))
        assertEquals("http://192.168.137.1:8000/", SettingsStore.normalize("http://192.168.137.1:8000/api/v1/"))
        assertEquals("https://example.com/", SettingsStore.normalize("  https://example.com/api/v1/ "))
    }

    @Test
    fun testBaseUrlRejection() {
        assertNull(SettingsStore.normalize(""))
        assertNull(SettingsStore.normalize("   "))
        assertNull(SettingsStore.normalize("http://"))
        assertNull(SettingsStore.normalize("http:///"))
    }

    @Test
    fun testEmotionFallback() {
        assertEquals(Emotion.HAPPY, Emotion.from("happy"))
        assertEquals(Emotion.HAPPY, Emotion.from(" HAPPY "))
        assertEquals(Emotion.SAD, Emotion.from("sad"))
        assertEquals(Emotion.SAD, Emotion.from(" SAD "))
        assertEquals(Emotion.SURPRISED, Emotion.from("surprised"))
        assertEquals(Emotion.SURPRISED, Emotion.from(" SURPRISED "))
        assertEquals(Emotion.NEUTRAL, Emotion.from("neutral"))
        assertEquals(Emotion.NEUTRAL, Emotion.from(" NEUTRAL "))
        assertEquals(Emotion.NEUTRAL, Emotion.from("unknown"))
        assertEquals(Emotion.NEUTRAL, Emotion.from("angry"))
        assertEquals(Emotion.NEUTRAL, Emotion.from(null))
        assertEquals(Emotion.NEUTRAL, Emotion.from(""))
        assertEquals(Emotion.NEUTRAL, Emotion.from("   "))
    }

    @Test
    fun testDeterministicMessageOrdering() {
        val timestamp = 1700000000000L
        val botMessage = MessageEntity(
            id = "msg_2",
            conversationId = "conv_1",
            role = "assistant",
            text = "Xin chào!",
            emotion = "happy",
            createdAt = timestamp
        )
        val userMessage = MessageEntity(
            id = "msg_1",
            conversationId = "conv_1",
            role = "user",
            text = "Chào bạn",
            emotion = null,
            createdAt = timestamp
        )

        val messages = listOf(botMessage, userMessage)
        val comparator = compareBy<MessageEntity> { it.createdAt }
            .thenBy { if (it.role == "user") 0 else 1 }
            .thenBy { it.id }

        val sorted = messages.sortedWith(comparator)
        assertEquals("msg_1", sorted[0].id)
        assertEquals("user", sorted[0].role)
        assertEquals("msg_2", sorted[1].id)
        assertEquals("assistant", sorted[1].role)
    }

    @Test
    fun testEmptyListSynchronizationLogic() {
        val localDatabaseCache = mutableListOf("conv_1", "conv_2")
        fun syncServerConversations(serverItems: List<String>) {
            if (serverItems.isEmpty()) {
                localDatabaseCache.clear()
            } else {
                localDatabaseCache.retainAll(serverItems)
                serverItems.forEach { if (!localDatabaseCache.contains(it)) localDatabaseCache.add(it) }
            }
        }

        // Test empty list from server clears local cache
        syncServerConversations(emptyList())
        assertEquals(0, localDatabaseCache.size)

        // Test non-empty list updates local cache
        syncServerConversations(listOf("conv_3"))
        assertEquals(1, localDatabaseCache.size)
        assertEquals("conv_3", localDatabaseCache[0])
    }

    @Test
    fun testClientIdCreationLogic() {
        var persistedClientId: String? = null
        fun getOrGenerateClientId(): String {
            return persistedClientId ?: UUID.randomUUID().toString().also { persistedClientId = it }
        }

        val firstCall = getOrGenerateClientId()
        assertNotNull(firstCall)
        assertNotEquals("", firstCall)

        val secondCall = getOrGenerateClientId()
        assertEquals(firstCall, secondCall)
    }

    @Test
    fun testRequestIdGenerationAndRetryLogic() {
        var currentRequestId: String? = null
        var pendingMessage: String? = null

        fun onSend(message: String) {
            val text = pendingMessage ?: message
            val rid = if (pendingMessage == null) {
                UUID.randomUUID().toString().also { currentRequestId = it }
            } else {
                currentRequestId ?: UUID.randomUUID().toString().also { currentRequestId = it }
            }
            pendingMessage = text
        }

        fun onSuccess() {
            currentRequestId = null
            pendingMessage = null
        }

        // 1. Send first message
        onSend("Message 1")
        val reqId1 = currentRequestId
        assertNotNull(reqId1)

        // Simulate failure -> pendingMessage remains
        // 2. Retry exact message
        onSend("Message 1")
        val reqId1Retry = currentRequestId
        assertEquals(reqId1, reqId1Retry)

        // 3. Success
        onSuccess()
        assertNull(currentRequestId)
        assertNull(pendingMessage)

        // 4. Send second new message
        onSend("Message 2")
        val reqId2 = currentRequestId
        assertNotNull(reqId2)
        assertNotEquals(reqId1, reqId2)
    }
}
