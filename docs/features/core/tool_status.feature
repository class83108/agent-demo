# language: zh-TW
Feature: 工具使用狀態顯示
  作為使用者
  我想要知道 Agent 正在使用哪些工具
  以便了解 Agent 的工作進度與思考過程

  Background:
    Given Agent 已啟動
    And 使用者已連線至聊天介面

  Rule: Agent 呼叫工具時應通知使用者

    Scenario: 顯示工具開始執行
      Given Agent 正在處理使用者的問題
      When Agent 決定呼叫 "read_file" 工具
      Then 前端應收到 tool_call 事件，狀態為 "started"
      And 事件應包含工具名稱與參數摘要
      And 前端應顯示工具執行中的狀態指示器

    Scenario: 顯示工具執行完成
      Given Agent 正在執行 "read_file" 工具
      When 工具執行完成
      Then 前端應收到 tool_call 事件，狀態為 "completed"
      And 前端應將狀態指示器更新為完成

    Scenario: 顯示工具執行失敗
      Given Agent 正在執行 "read_file" 工具
      When 工具執行發生錯誤
      Then 前端應收到 tool_call 事件，狀態為 "failed"
      And 事件應包含錯誤訊息
      And 前端應將狀態指示器更新為失敗

  Rule: 工具狀態應顯示名稱與參數摘要

    Scenario: 讀取檔案時顯示檔案路徑
      When Agent 呼叫 "read_file" 工具，參數為 path="src/main.py"
      Then 狀態應顯示為「讀取檔案 src/main.py」

    Scenario: 搜尋程式碼時顯示搜尋模式
      When Agent 呼叫 "grep_search" 工具，參數為 pattern="logger"
      Then 狀態應顯示為「搜尋程式碼 logger」

    Scenario: 編輯檔案時顯示檔案路徑
      When Agent 呼叫 "edit_file" 工具，參數為 path="src/main.py"
      Then 狀態應顯示為「編輯檔案 src/main.py」

    Scenario: 執行命令時顯示命令摘要
      When Agent 呼叫 "bash" 工具，參數為 command="uv run pytest"
      Then 狀態應顯示為「執行命令 uv run pytest」

    Scenario: 列出檔案時顯示路徑
      When Agent 呼叫 "list_files" 工具，參數為 path="src/"
      Then 狀態應顯示為「列出檔案 src/」

  Rule: 工具呼叫前的文字應與最終回覆區隔

    Scenario: Preamble 文字預設折疊
      Given Agent 串流回應文字 "讓我查看一下程式碼..."
      When Agent 接著呼叫工具
      Then 前端應收到 preamble_end 事件
      And 之前的文字應被標記為 preamble
      And preamble 預設應折疊顯示

    Scenario: 使用者可展開 preamble
      Given preamble 文字已折疊
      When 使用者點擊 preamble 區域
      Then preamble 應展開顯示完整內容

    Scenario: 多次工具呼叫產生多個 preamble
      Given Agent 先呼叫 "read_file" 工具
      And Agent 串流更多文字 "接下來我會搜尋..."
      When Agent 再呼叫 "grep_search" 工具
      Then 應產生兩段獨立的 preamble
      And 每段 preamble 各自可折疊展開

  Rule: 工具狀態與 preamble 的顯示順序

    Scenario: 完整的工具呼叫流程
      Given Agent 正在回應使用者
      When Agent 完成一輪工具呼叫
      Then 顯示順序應為：
        | 順序 | 內容             |
        | 1    | preamble（折疊） |
        | 2    | 工具狀態（已完成）|
        | 3    | 最終回覆文字     |
