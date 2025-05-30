package com.example.service;

import com.example.entity.ChatMessage;

/**
 * 聊天服务接口
 * 定义了处理聊天消息的核心业务逻辑
 */
public interface ChatService {

  ChatMessage processMessage(String message, String sessionId);

  String createNewSession();
}