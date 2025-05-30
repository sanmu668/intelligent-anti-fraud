package com.example.service.impl;

import com.example.entity.ChatMessage;
import com.example.service.ChatService;
import com.example.service.ChatHistoryService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.alibaba.dashscope.aigc.generation.Generation;
import com.alibaba.dashscope.aigc.generation.GenerationResult;
import com.alibaba.dashscope.aigc.generation.models.QwenParam;
import com.alibaba.dashscope.common.Message;
import com.alibaba.dashscope.common.Role;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * ChatService接口的实现类
 * 使用DashScope SDK实现与AI模型的交互
 */
@Service
public class ChatServiceImpl implements ChatService {

  private static final Logger logger = LoggerFactory.getLogger(ChatServiceImpl.class);

  @Autowired
  private ChatHistoryService chatHistoryService;

  @Value("${dashscope.api.key}")
  private String apiKey;

  @Value("${dashscope.model}")
  private String model;

  @Override
  public ChatMessage processMessage(String message, String sessionId) {
    try {
      ChatMessage userMessage = ChatMessage.createUserMessage(sessionId, message);
      chatHistoryService.addMessage(userMessage);

      Generation gen = new Generation();

      List<Message> messages = new ArrayList<>();

      messages.add(Message.builder()
          .role(Role.SYSTEM.getValue())
          .content("你是FraudGuard，一名专业金融反欺诈AI助手。你的职责是：\n"+
              "1. 检测用户交易中的可疑行为\n" +
              "2. 回答用户关于诈骗风险的问题\n" +
              "3. 提供防骗建议。语气专业、简洁、具备风控意识。")
          .build());

      for (ChatMessage historyMessage : chatHistoryService.getSessionHistory(sessionId)) {
        messages.add(Message.builder()
            .role(historyMessage.getType().equals("user") ? Role.USER.getValue() : Role.ASSISTANT.getValue())
            .content(historyMessage.getContent())
            .build());
      }

      QwenParam param = QwenParam.builder()
          .model(model)
          .messages(messages)
          .resultFormat(QwenParam.ResultFormat.MESSAGE)
          .apiKey(apiKey) // 显式设置API密钥
          .build();

      GenerationResult result = gen.call(param);

      ChatMessage response = ChatMessage.createAiMessage(
          sessionId,
          result.getOutput().getChoices().get(0).getMessage().getContent());

      chatHistoryService.addMessage(response);

      return response;

    } catch (NoApiKeyException e) {
      logger.error("DashScope API密钥未找到或无效", e);
      throw new RuntimeException("AI服务配置错误，请联系管理员", e);
    } catch (InputRequiredException e) {
      logger.error("输入参数无效", e);
      throw new RuntimeException("输入参数无效", e);
    } catch (ApiException e) {
      logger.error("API调用失败", e);
      throw new RuntimeException("AI服务暂时不可用，请稍后重试", e);
    }
  }

  @Override
  public String createNewSession() {
    String sessionId = String.valueOf(System.currentTimeMillis());
    return sessionId;
  }
}