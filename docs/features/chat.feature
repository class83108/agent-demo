# language: zh-TW
Feature: 基礎聊天功能
  作為使用者
  我想要與 Agent 進行對話
  以便獲得程式開發上的協助

  Background:
    Given Agent 已啟動
    And 系統提示詞已設定為程式助手角色

  Rule: Agent 應回應使用者的訊息

    Scenario: 使用者發送簡單問題
      When 使用者輸入 "什麼是 Python?"
      Then Agent 應回傳包含 Python 說明的回應
      And 回應應為繁體中文

    Scenario: 使用者發送程式相關問題
      When 使用者輸入 "如何在 Python 中讀取 JSON 檔案?"
      Then Agent 應回傳包含程式碼範例的回應
      And 程式碼應使用正確的語法高亮標記

    Scenario: 使用者發送空白訊息
      When 使用者輸入空白訊息
      Then Agent 應提示使用者輸入有效內容

    Scenario: 使用者發送過長訊息
      When 使用者輸入超過 token 限制的訊息
      Then Agent 應回傳適當的錯誤提示

  Rule: 對話應保持上下文連貫

    Scenario: Agent 記住先前的對話
      Given 使用者曾詢問 "Python 是什麼?"
      And Agent 已回答關於 Python 的說明
      When 使用者輸入 "它有哪些優點?"
      Then Agent 應根據 Python 的上下文回答
      And 回應應提及 Python 的優點

    Scenario: 多輪對話保持一致性
      Given 使用者曾詢問如何定義函數
      And Agent 提供了函數定義範例
      When 使用者詢問 "如何加上型別註解?"
      Then Agent 應在先前的函數範例基礎上加入型別註解

  Rule: Agent 應正確處理錯誤情況

    Scenario: API 連線失敗
      Given API 服務暫時無法連線
      When 使用者輸入任何訊息
      Then Agent 應回傳連線錯誤提示
      And 提示應建議使用者稍後重試

    Scenario: API 金鑰無效
      Given API 金鑰設定錯誤
      When 使用者輸入任何訊息
      Then Agent 應回傳認證錯誤提示
      And 提示應說明如何設定正確的 API 金鑰

    Scenario: API 回應超時
      Given API 回應時間超過設定的超時閾值
      When 使用者輸入任何訊息
      Then Agent 應回傳超時錯誤提示

  Rule: Agent 應支援串流回應

    Scenario: 即時顯示回應內容
      When 使用者輸入問題
      Then Agent 應以串流方式逐步顯示回應
      And 使用者應能即時看到回應生成過程

    Scenario: 串流中斷處理
      Given Agent 正在串流回應
      When 串流連線意外中斷
      Then Agent 應顯示已接收的部分回應
      And Agent 應提示串流中斷
