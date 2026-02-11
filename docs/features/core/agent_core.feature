# language: zh-TW
Feature: Agent 核心架構
  作為開發者
  我想要一個穩定的 Agent Loop 架構
  以便能夠擴展各種工具並處理複雜任務

  Background:
    Given Agent 已初始化
    And API 金鑰已設定

  Rule: Agent Loop 應持續運作直到任務完成

    Scenario: 單輪對話無工具調用
      Given 使用者輸入不需要工具的問題
      When Agent 處理該輸入
      Then Agent 應直接回傳 Claude 的回應
      And 對話歷史應包含一輪交互

    Scenario: 單輪對話有工具調用
      Given 使用者輸入需要工具的問題
      When Agent 處理該輸入
      Then Agent 應執行所需工具
      And Agent 應將工具結果傳回 Claude
      And Agent 應回傳最終回應

    Scenario: 多輪工具調用
      Given 使用者輸入需要多次工具調用的複雜任務
      When Agent 處理該輸入
      Then Agent 應依序執行每輪所需的工具
      And Agent 應在所有工具完成後回傳最終回應

  Rule: Agent 應支援並行工具執行

    Scenario: 同時執行多個獨立工具
      Given Claude 回應包含多個工具調用請求
      And 這些工具調用彼此獨立
      When Agent 執行這些工具
      Then 所有工具應並行執行
      And Agent 應收集所有結果後一併回傳給 Claude

    Scenario: 並行執行中部分工具失敗
      Given Claude 回應包含三個工具調用請求
      When Agent 並行執行這些工具
      And 其中一個工具執行失敗
      Then Agent 應收集成功的結果與失敗的錯誤訊息
      And Agent 應將所有結果回傳給 Claude 處理

  Rule: Agent 應維護對話歷史

    Scenario: 保持上下文連貫性
      Given 使用者已進行過多輪對話
      When 使用者提問涉及先前對話內容
      Then Agent 應能根據歷史上下文回答

    Scenario: 對話歷史包含工具調用記錄
      Given 使用者曾觸發工具調用
      When 查看對話歷史
      Then 歷史應包含工具調用請求與結果

  Rule: Tool Registry 應能動態管理工具

    Scenario: 註冊新工具
      Given Tool Registry 已初始化
      When 註冊一個新工具
      Then 該工具應出現在可用工具列表中
      And Claude 請求應包含該工具的定義

    Scenario: 執行已註冊的工具
      Given Tool Registry 包含 "read_file" 工具
      When Claude 請求執行 "read_file" 工具
      Then Agent 應找到並執行該工具
      And 應回傳工具執行結果

    Scenario: 處理未知工具調用
      Given Tool Registry 不包含 "unknown_tool" 工具
      When Claude 請求執行 "unknown_tool" 工具
      Then Agent 應回傳錯誤訊息
      And 錯誤訊息應說明工具不存在

  Rule: Agent 應透過 Provider 抽象層呼叫 LLM

    Scenario: Agent 使用注入的 Provider
      Given Agent 已配置 AnthropicProvider
      When 使用者發送訊息
      Then Agent 應透過 Provider 發送 API 請求
      And 不應直接使用 anthropic SDK

  Rule: Agent 應整合 Skill 系統

    Scenario: Agent 使用已啟用 Skill 的 System Prompt
      Given Agent 基礎 prompt 為 "你是助手"
      And SkillRegistry 包含 Skill "fitness"（instructions 為 "你擅長健身"）
      And Skill "fitness" 已被啟用
      When Agent 發送 API 請求
      Then system prompt 應包含基礎 prompt 與 Skill 描述清單
      And system prompt 應包含 "fitness" 的完整 instructions

    Scenario: 未啟用的 Skill 不注入完整指令
      Given Agent 基礎 prompt 為 "你是助手"
      And SkillRegistry 包含 Skill "fitness" 但未啟用
      When Agent 發送 API 請求
      Then system prompt 應包含 Skill 描述清單
      And system prompt 不應包含 "fitness" 的完整 instructions
