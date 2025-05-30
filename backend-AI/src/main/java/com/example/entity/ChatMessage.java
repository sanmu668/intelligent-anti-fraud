package com.example.entity;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 聊天消息实体类
 * 用于封装聊天消息的相关信息
 */
@Data
public class ChatMessage {

  private String id;

  private String sessionId;

  private String content;

  private String type;

  private LocalDateTime timestamp;
  public static ChatMessage createUserMessage(String sessionId, String content) {
    ChatMessage message = new ChatMessage();
    message.setSessionId(sessionId);
    message.setContent(content);
    message.setType("user");
    message.setTimestamp(LocalDateTime.now());
    return message;
  }

  public static ChatMessage createAiMessage(String sessionId, String content) {
    ChatMessage message = new ChatMessage();

    message.setSessionId(sessionId);
    message.setContent(content);

    message.setType("ai");
    message.setTimestamp(LocalDateTime.now());

    return message;
  }

}