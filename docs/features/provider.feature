# language: zh-TW
Feature: LLM Provider 抽象層
  作為開發者
  我想要可抽換的 LLM Provider
  以便未來支援不同的 AI 模型服務

  Rule: Provider 應封裝 LLM 特定邏輯

    Scenario: Anthropic Provider 串流回應
      Given 已建立 AnthropicProvider
      When 透過 Provider 發送訊息
      Then 應以 AsyncIterator 逐步回傳 token
      And 最終回傳包含 content 和 stop_reason 的結果

    Scenario: Anthropic Provider 處理工具調用
      Given 已建立 AnthropicProvider
      When Claude 回應包含 tool_use block
      Then Provider 應回傳 stop_reason 為 "tool_use"
      And content 應包含 tool_use block 的完整資訊

  Rule: Provider 應轉換特定例外為通用例外

    Scenario: API 金鑰無效
      Given Anthropic API 回傳 AuthenticationError
      When Provider 處理該錯誤
      Then 應拋出 ProviderAuthError

    Scenario: API 連線失敗
      Given Anthropic API 回傳 APIConnectionError
      When Provider 處理該錯誤
      Then 應拋出 ProviderConnectionError

    Scenario: API 回應超時
      Given Anthropic API 回傳 APITimeoutError
      When Provider 處理該錯誤
      Then 應拋出 ProviderTimeoutError

  Rule: Anthropic Provider 應支援 Prompt Caching

    Scenario: 在 system prompt 加上 cache_control
      Given enable_prompt_caching 為 True
      When Provider 建立 API 請求
      Then system prompt 應包含 cache_control ephemeral

    Scenario: 在工具定義最後加上 cache_control
      Given enable_prompt_caching 為 True
      And 有已註冊的工具
      When Provider 建立 API 請求
      Then 最後一個工具定義應包含 cache_control ephemeral

    Scenario: 停用 Prompt Caching
      Given enable_prompt_caching 為 False
      When Provider 建立 API 請求
      Then 不應包含任何 cache_control
