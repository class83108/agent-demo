# language: zh-TW
Feature: Agent 配置系統
  作為開發者
  我想要彈性配置 Agent 的行為
  以便在不同場景使用不同的模型與設定

  Rule: 應支援配置 LLM Provider

    Scenario: 使用預設配置建立 Agent
      Given 未提供任何配置
      When 建立 AgentCoreConfig
      Then Provider 類型應為 "anthropic"
      And 模型應為預設值

    Scenario: 自訂模型與 API Key
      Given 配置指定模型為 "claude-haiku-4-20250514"
      And 配置指定 API Key 為 "sk-test-key"
      When 建立 Agent
      Then Agent 應使用指定的模型
      And Agent 應使用指定的 API Key

    Scenario: API Key 從環境變數讀取
      Given 配置未指定 API Key
      And 環境變數 ANTHROPIC_API_KEY 已設定
      When 建立 AnthropicProvider
      Then Provider 應使用環境變數中的 API Key

  Rule: 應支援配置 System Prompt

    Scenario: 自訂 System Prompt
      Given 配置指定 system_prompt 為 "你是健身教練"
      When Agent 發送 API 請求
      Then 請求的 system prompt 應包含 "你是健身教練"
