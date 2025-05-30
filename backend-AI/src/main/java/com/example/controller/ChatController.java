package com.example.controller;

import com.example.entity.ChatMessage;
import com.example.service.ChatService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * 聊天功能的REST控制器
 * 处理所有与聊天相关的HTTP请求
 */
@RestController
@RequestMapping("/chat")
@CrossOrigin(origins = "*", allowedHeaders = "*")
public class ChatController {

  /**
   * 日志记录器实例
   */
  private static final Logger logger = LoggerFactory.getLogger(ChatController.class);

  @Autowired
  private ChatService chatService;
  @PostMapping("/message")
  public ResponseEntity<ChatMessage> sendMessage(@RequestBody ChatRequestDTO request) {
    if (request.getMessage() == null || request.getMessage().trim().isEmpty()) {
      return ResponseEntity.badRequest().build();
    }

    logger.debug("Received message request - sessionId: {}, message: {}",
        request.getSessionId(), request.getMessage());

    ChatMessage response = chatService.processMessage(
        request.getMessage(),
        request.getSessionId());

    logger.debug("Sending response: {}", response);

    return ResponseEntity.ok(response);
  }

  @PostMapping("/new-session")
  public ResponseEntity<ChatMessage> createNewSession() {
    String sessionId = String.valueOf(System.currentTimeMillis());
    ChatMessage response = new ChatMessage();
    response.setSessionId(sessionId);
    return ResponseEntity.ok(response);
  }
}

class ChatRequestDTO {
  private String message;
  private String sessionId;

  public String getMessage() {
    return message;
  }

  public void setMessage(String message) {
    this.message = message;
  }

  public String getSessionId() {
    return sessionId;
  }

  public void setSessionId(String sessionId) {
    this.sessionId = sessionId;
  }
}