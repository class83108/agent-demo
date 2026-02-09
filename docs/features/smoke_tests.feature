# language: zh-TW
Feature: Smoke Tests — 端對端驗證各模組實際運作
  作為框架開發者
  我想要有 Smoke Test 驗證各模組在真實 API 下的行為
  以便確保核心功能在整合後仍正常運作

  Background:
    Given 已設定 ANTHROPIC_API_KEY 環境變數
    And 使用 --run-smoke 參數執行測試

  Rule: Token Counter 應在真實 API 呼叫後正確追蹤使用量

    Scenario: 對話後 token 使用量大於零
      Given Agent 已啟動且配置 TokenCounter
      When 使用者傳送一則訊息並取得回應
      Then token_counter.total_input_tokens 應大於 0
      And token_counter.total_output_tokens 應大於 0
      And token_counter.usage_percent 應大於 0

    Scenario: 多輪對話後 token 使用量累計增長
      Given Agent 已啟動且配置 TokenCounter
      When 使用者連續傳送兩則訊息
      Then 第二輪後的 total_input_tokens 應大於第一輪

  Rule: Tool Result 分頁應在結果過大時自動觸發

    Scenario: 讀取大檔案時自動分頁
      Given Agent 已啟動且啟用內建工具
      And 沙箱中有一個超過分頁閾值的大檔案
      When 使用者要求讀取該大檔案
      Then Agent 應取得分頁後的結果（含 [Page 1/N] 標記）
      And Agent 能正常回應檔案內容

  Rule: Compact 應在 context window 使用率高時壓縮對話

    Scenario: Phase 2 LLM 摘要 — 純文字多輪對話觸發摘要
      Given Agent 已啟動且配置 TokenCounter
      And compact 閾值已調低以便測試觸發
      And 不使用任何工具（避免 Phase 1 截斷導致提早返回）
      When 使用者連續進行多輪純文字對話直到超過閾值
      Then compact 應被觸發
      And 對話歷史應被替換為摘要訊息加上保留的最近訊息
      And 摘要訊息的 role 應為 user 且內容包含「摘要」

  Rule: Multimodal 應支援圖片輸入

    Scenario: 傳送圖片並取得描述
      Given Agent 已啟動
      And 準備一張測試用 PNG 圖片（含可辨識的內容）
      When 使用者傳送包含該圖片的訊息並詢問圖片內容
      Then Agent 應回應包含圖片內容描述的文字

  Rule: Skill 應能實際改變 Agent 的回應行為

    Scenario: SEO Skill — 啟用後回應中應包含指定關鍵字
      Given Agent 已啟動
      And 已註冊並啟用一個 SEO Skill，instructions 要求在每次回應中加入關鍵字 "AgentCore" 和 "框架"
      When 使用者詢問一個與關鍵字無關的問題（例如「天氣如何？」）
      Then Agent 的回應中應包含關鍵字 "AgentCore"
      And Agent 的回應中應包含關鍵字 "框架"

  Rule: MCP Server 應能透過真實 npx 啟動並提供工具

    Scenario: 連接真實 MCP Server 並列出工具
      Given 系統已安裝 npx（若無則跳過此測試）
      And 啟動一個 MCP Server（例如 @modelcontextprotocol/server-memory）
      When 透過 MCPClient 取得工具列表
      Then 工具列表應不為空
      And 每個工具應有 name 和 description
