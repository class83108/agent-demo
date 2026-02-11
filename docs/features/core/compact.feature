# language: zh-TW
Feature: 上下文壓縮（Compact）
  作為 Agent 系統
  我想要在對話接近 context window 上限時自動壓縮
  以便讓長對話可以持續進行而不中斷

  Background:
    Given Agent 已啟動並設定 context window 上限

  Rule: 應截斷舊的工具結果以釋放空間（Phase 1）

    Scenario: 截斷舊的 tool_result 內容
      Given 對話歷史中包含多輪工具調用結果
      When 執行 Phase 1 截斷
      Then 舊的 tool_result 內容應被替換為壓縮標記
      And 對應的 tool_use block 應保留不變

    Scenario: 保留最近一輪的 tool_result
      Given 對話歷史中包含多輪工具調用結果
      When 執行 Phase 1 截斷
      Then 最近一輪的 tool_result 不應被截斷

    Scenario: 無 tool_result 時不變
      Given 對話歷史中不包含任何工具調用
      When 執行 Phase 1 截斷
      Then 對話歷史應保持不變

  Rule: 應用 LLM 摘要早期對話以進一步壓縮（Phase 2）

    Scenario: 摘要早期對話
      Given Phase 1 截斷後仍超過閾值
      When 執行 Phase 2 LLM 摘要
      Then 早期的對話輪次應被替換為摘要訊息
      And 摘要訊息格式為 user 摘要 + assistant 確認

    Scenario: 保留最近的訊息不被摘要
      Given 對話歷史中有多輪對話
      When 執行 Phase 2 LLM 摘要
      Then 最近的訊息輪次不應被摘要

  Rule: Compact 流程應按階段執行

    Scenario: Phase 1 足夠時不觸發 Phase 2
      Given 對話接近 context window 上限
      And Phase 1 截斷後已低於閾值
      When 執行 compact 流程
      Then 應只執行 Phase 1
      And 不應呼叫 LLM 進行摘要

    Scenario: Phase 1 不足時觸發 Phase 2
      Given 對話接近 context window 上限
      And Phase 1 截斷後仍超過閾值
      When 執行 compact 流程
      Then 應先執行 Phase 1 再執行 Phase 2

  Rule: Agent 應在適當時機自動觸發 compact

    Scenario: 超過閾值時自動觸發 compact
      Given Agent 的 context window 使用率超過 80%
      When Agent 進行下一次 API 呼叫前
      Then 應自動觸發 compact 流程
      And 應發送 compact 事件通知前端

    Scenario: 未超過閾值時不觸發 compact
      Given Agent 的 context window 使用率低於 80%
      When Agent 進行下一次 API 呼叫前
      Then 不應觸發 compact 流程
