package com.example.service;

import com.example.entity.ChatMessage;
import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 聊天历史记录管理服务
 */
@Service
public class ChatHistoryService {

  private final Map<String, List<ChatMessage>> sessionHistories = new ConcurrentHashMap<>();

  public void addMessage(ChatMessage message) {
    String sessionId = message.getSessionId();
    sessionHistories.computeIfAbsent(sessionId, k -> new ArrayList<>()).add(message);

    List<ChatMessage> history = sessionHistories.get(sessionId);
    if (history.size() > 10) {
      sessionHistories.put(sessionId, history.subList(history.size() - 10, history.size()));
    }
  }

  public List<ChatMessage> getSessionHistory(String sessionId) {
    return sessionHistories.getOrDefault(sessionId, new ArrayList<>());
  }

  public void clearSessionHistory(String sessionId) {
    sessionHistories.remove(sessionId);
  }
}