package com.example.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * DashScope配置类
 * 负责初始化DashScope SDK的配置
 */
@Configuration
public class DashScopeConfig {

  private static final Logger logger = LoggerFactory.getLogger(DashScopeConfig.class);

  /**
   * DashScope API密钥
   * 从配置文件中通过@Value注解注入
   */
  @Value("${dashscope.api.key}")
  private String apiKey;

  @Value("${spring.ai.dashscope.chat.options.model}")
  private String model;

  @PostConstruct
  public void init() {

    logger.info("正在初始化DashScope配置...");
    try {
      System.setProperty("dashscope.api.key", apiKey);
      logger.info("DashScope配置初始化完成");
    } catch (Exception e) {
      logger.error("DashScope配置初始化失败", e);
      throw new IllegalStateException("DashScope配置初始化失败", e);
    }
  }

  public String getApiKey() {
    return apiKey;
  }

  public String getModel() {
    return model;
  }
}