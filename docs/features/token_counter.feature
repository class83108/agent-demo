# language: zh-TW
Feature: Token 計數
  作為 Agent 系統
  我想要追蹤當前對話的 token 使用量
  以便在接近 context window 上限時觸發壓縮機制

  Rule: Token 計數器應在每次 API 回應後更新

    Scenario: 首次 API 回應後更新 token 計數
      Given TokenCounter 已初始化，context window 為 200000
      And 目前尚無 token 記錄
      When 收到 API 回應，input_tokens=1000, output_tokens=500
      Then current_context_tokens 應為 1500
      And usage_percent 應為 0.75

    Scenario: 多輪對話後 token 計數反映最新狀態
      Given TokenCounter 已初始化
      And 前一次 API 回應的 input_tokens=1000, output_tokens=500
      When 收到新的 API 回應，input_tokens=2000, output_tokens=800
      Then current_context_tokens 應為 2800
      And 計數器應反映最新一次的 context 狀態

  Rule: 應正確計算含快取的 token 數

    Scenario: API 回應包含快取 token
      Given TokenCounter 已初始化，context window 為 200000
      When 收到 API 回應，input_tokens=500, cache_creation=300, cache_read=200, output_tokens=400
      Then current_context_tokens 應為 1400
      And usage_percent 應為 0.7

  Rule: 應正確計算 context window 使用百分比

    Scenario: 低使用量
      Given TokenCounter 已初始化，context window 為 200000
      When 收到 API 回應，input_tokens=10000, output_tokens=5000
      Then usage_percent 應為 7.5

    Scenario: 接近上限
      Given TokenCounter 已初始化，context window 為 200000
      When 收到 API 回應，input_tokens=150000, output_tokens=20000
      Then usage_percent 應為 85.0

  Rule: 應透過 API 端點回傳 token 使用量

    Scenario: /api/agent/status 包含 context window 資訊
      When 查詢 /api/agent/status
      Then 回應應包含 context_window 欄位
      And context_window 值應對應目前模型的上限

    Scenario: /api/chat/usage 包含 context 區塊
      Given 已有一個進行中的 session，且已有 API 呼叫記錄
      When 查詢 /api/chat/usage
      Then 回應應包含 context 區塊
      And context 區塊應包含 current_tokens、context_window、usage_percent

  Rule: 支援精確 token 計數

    Scenario: 透過 provider 的 count_tokens API 精確計數
      Given Agent 已初始化並有對話歷史
      When 呼叫 provider.count_tokens() 計算目前 conversation 的 token 數
      Then 應回傳精確的 input token 數量
