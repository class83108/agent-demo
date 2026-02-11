# language: zh-TW
Feature: Skill 技能系統
  作為開發者
  我想要以 Skill 為單位擴充 Agent 的能力
  以便模組化管理不同領域的 prompt 指令

  Background:
    Given SkillRegistry 已初始化

  Rule: Skill 應支援註冊與管理

    Scenario: 註冊一個 Skill
      Given 建立一個 Skill 包含 name、description 和 instructions
      When 將 Skill 註冊到 SkillRegistry
      Then SkillRegistry 應包含該 Skill

    Scenario: 註冊多個 Skill
      Given 建立 Skill A 和 Skill B
      When 將兩個 Skill 都註冊到 SkillRegistry
      Then SkillRegistry 應包含 2 個 Skill

    Scenario: 不允許重複註冊同名 Skill
      Given SkillRegistry 已包含名為 "fitness" 的 Skill
      When 嘗試註冊另一個名為 "fitness" 的 Skill
      Then 應拋出 ValueError
      And 錯誤訊息應說明 Skill 名稱重複

  Rule: Skill 應支援兩階段載入

    Scenario: Phase 1 — 只載入 Skill 描述清單
      Given SkillRegistry 包含 "fitness"（description 為 "健身紀錄助手"）
      And SkillRegistry 包含 "nutrition"（description 為 "營養建議"）
      When 取得 Skill 描述清單
      Then 結果應包含 "fitness" 與 "健身紀錄助手"
      And 結果應包含 "nutrition" 與 "營養建議"

    Scenario: Phase 1 — 隱藏 disable_model_invocation 的 Skill
      Given SkillRegistry 包含 Skill A（disable_model_invocation 為 False）
      And SkillRegistry 包含 Skill B（disable_model_invocation 為 True）
      When 取得 Skill 描述清單
      Then 結果應只包含 Skill A 的描述
      And 結果不應包含 Skill B 的描述

    Scenario: Phase 2 — 啟用 Skill 載入完整指令
      Given SkillRegistry 包含 Skill 其 instructions 為 "你擅長健身建議"
      And 該 Skill 尚未啟用
      When 啟用該 Skill
      Then 該 Skill 應出現在已啟用列表中

    Scenario: 停用已啟用的 Skill
      Given Skill "fitness" 已被啟用
      When 停用 Skill "fitness"
      Then "fitness" 不應出現在已啟用列表中

  Rule: Skill 應能擴充 System Prompt

    Scenario: 合併基礎提示、描述清單與已啟用 Skill 指令
      Given 基礎 system_prompt 為 "你是一位助手"
      And SkillRegistry 包含 "fitness" 和 "nutrition" 兩個 Skill
      And "fitness" 已被啟用
      When 呼叫 get_combined_system_prompt("你是一位助手")
      Then 結果應包含 "你是一位助手"
      And 結果應包含 Skill 描述清單
      And 結果應包含 "fitness" 的完整 instructions
      And 結果不應包含 "nutrition" 的完整 instructions

    Scenario: 無 Skill 時只回傳基礎提示
      Given SkillRegistry 為空
      When 呼叫 get_combined_system_prompt("你是一位助手")
      Then 結果應為 "你是一位助手"

  Rule: Skill 應能列出與查詢

    Scenario: 列出所有已註冊的 Skill
      Given SkillRegistry 包含 "fitness" 和 "nutrition" 兩個 Skill
      When 列出所有 Skill
      Then 應回傳包含 "fitness" 和 "nutrition" 的列表

    Scenario: 依名稱取得 Skill
      Given SkillRegistry 包含名為 "fitness" 的 Skill
      When 以名稱 "fitness" 查詢
      Then 應回傳該 Skill 的完整資訊

    Scenario: 查詢不存在的 Skill
      Given SkillRegistry 為空
      When 以名稱 "unknown" 查詢
      Then 應回傳 None
