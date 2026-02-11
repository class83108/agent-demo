# language: zh-TW
Feature: 聊天 API 端點
  作為開發者
  我想要透過 HTTP API 與前端進行聊天
  以便將 Agent 功能暴露給瀏覽器客戶端

  Background:
    Given API 伺務已啟動
    And Redis 會話儲存已連接

  Rule: SSE 端點應正確串流回傳 Agent 回應

    Scenario: 正常訊息透過 SSE 逐步傳回
      When 客戶端發送 POST /api/chat/stream 帶有有效訊息
      Then 回應 Content-Type 應為 text/event-stream
      And 應收到若干個 event: token 事件
      And 應收到一個 event: done 事件
      And 所有 token 組合後應為完整回應

    Scenario: 空白訊息傳回 SSE error 事件
      When 客戶端發送 POST /api/chat/stream 帶有空白訊息
      Then 應收到一個 event: error 事件
      And 錯誤類型應為 ValueError

    Scenario: Agent 拋出 ConnectionError 時傳回 SSE error 事件
      Given Agent 的 API 連線將失敗
      When 客戶端發送 POST /api/chat/stream
      Then 應收到一個 event: error 事件
      And 錯誤類型應為 ConnectionError

  Rule: 會話 Cookie 應自動管理

    Scenario: 首次請求生成新會話 Cookie
      Given 客戶端未攜帶 session_id Cookie
      When 客戶端發送 POST /api/chat/stream
      Then 回應應包含 Set-Cookie: session_id
      And Cookie 應設定 max_age 為 86400 秒（24 小時）

    Scenario: 既有會話應更新 Cookie 過期時間
      Given 客戶端已攜帶有效的 session_id Cookie
      When 客戶端發送 POST /api/chat/stream
      Then 回應應包含 Set-Cookie: session_id
      And Cookie 的 max_age 應更新為 86400 秒

  Rule: 會話歷史應透過 Redis 持久化

    Scenario: 連續對話歷史累積正確
      Given 客戶端攜帶 session_id Cookie
      And 該會話已有一組對話歷史
      When 客戶端發送第二則訊息
      And 串流完成
      Then Redis 中該會話的歷史應包含兩組 user 和 assistant 訊息

    Scenario: 清除會話歷史
      Given 客戶端攜帶有效的 session_id Cookie
      When 客戶端發送 POST /api/chat/reset
      Then 該會話的歷史應從 Redis 中刪除
      And 回應狀態碼應為 200

  Rule: 會話歷史應可透過 API 讀取

    Scenario: 取得現有會話的歷史記錄
      Given 客戶端攜帶有效的 session_id Cookie
      And 該會話已有兩組對話歷史
      When 客戶端發送 GET /api/chat/history
      Then 回應狀態碼應為 200
      And 回應 JSON 應包含 messages 陣列
      And messages 陣列應包含兩組 user 和 assistant 訊息
      And 每則訊息應包含 role 和 content 欄位

    Scenario: 取得空會話的歷史記錄
      Given 客戶端攜帶有效的 session_id Cookie
      And 該會話無任何對話歷史
      When 客戶端發送 GET /api/chat/history
      Then 回應狀態碼應為 200
      And 回應 JSON 的 messages 陣列應為空

    Scenario: 無會話時取得歷史記錄
      Given 客戶端未攜帶 session_id Cookie
      When 客戶端發送 GET /api/chat/history
      Then 回應狀態碼應為 200
      And 回應 JSON 的 messages 陣列應為空
