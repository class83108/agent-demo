# language: zh-TW
Feature: 即時檔案變更預覽
  作為使用者
  我想要在瀏覽器上即時看到 Agent 對檔案的修改
  以便清楚了解 Agent 做了哪些程式碼變更

  Background:
    Given API 伺服器已啟動
    And Sandbox 資料夾已初始化
    And 前端已連接 SSE 串流

  Rule: Sandbox 應限制 Agent 的操作範圍

    Scenario: Agent 只能操作 Sandbox 內的檔案
      Given Sandbox 路徑為 "workspace/sandbox"
      When Agent 嘗試讀取 "workspace/sandbox/src/main.py"
      Then 操作應成功

    Scenario: Agent 無法操作 Sandbox 外的檔案
      Given Sandbox 路徑為 "workspace/sandbox"
      When Agent 嘗試讀取 "workspace/config.json"
      Then 操作應被拒絕
      And 應回傳權限錯誤訊息

    Scenario: Agent 無法透過路徑穿越離開 Sandbox
      Given Sandbox 路徑為 "workspace/sandbox"
      When Agent 嘗試讀取 "workspace/sandbox/../config.json"
      Then 操作應被拒絕
      And 應回傳安全性錯誤訊息

  Rule: 檔案讀取時應透過 SSE 推送內容至前端

    Scenario: Agent 讀取檔案時前端收到檔案內容
      Given Sandbox 內存在檔案 "src/utils.py" 包含程式碼
      When Agent 調用 read_file 工具讀取 "src/utils.py"
      Then 前端應收到 SSE 事件 "file_open"
      And 事件資料應包含檔案路徑 "src/utils.py"
      And 事件資料應包含檔案完整內容

    Scenario: file_open 事件的資料格式
      When 前端收到 "file_open" 事件
      Then 事件資料應為 JSON 格式
      And 應包含欄位 "path" 為檔案相對路徑
      And 應包含欄位 "content" 為檔案內容
      And 應包含欄位 "language" 為程式語言識別

  Rule: 檔案編輯時應透過 SSE 推送差異至前端

    Scenario: Agent 編輯檔案時前端收到 diff
      Given Sandbox 內存在檔案 "src/utils.py" 包含原始內容
      When Agent 調用 edit_file 工具修改 "src/utils.py"
      Then 前端應收到 SSE 事件 "file_change"
      And 事件資料應包含 unified diff 格式的差異

    Scenario: file_change 事件的資料格式
      When 前端收到 "file_change" 事件
      Then 事件資料應為 JSON 格式
      And 應包含欄位 "path" 為檔案相對路徑
      And 應包含欄位 "diff" 為 unified diff 字串

    Scenario: 新建檔案時的 diff 格式
      Given Sandbox 內不存在檔案 "src/new_module.py"
      When Agent 調用 edit_file 工具建立 "src/new_module.py"
      Then 前端應收到 SSE 事件 "file_change"
      And diff 應顯示所有內容為新增（以 + 開頭）

    Scenario: 刪除檔案內容時的 diff 格式
      Given Sandbox 內存在檔案 "src/old.py" 包含內容
      When Agent 調用 edit_file 工具清空 "src/old.py"
      Then 前端應收到 SSE 事件 "file_change"
      And diff 應顯示所有內容為刪除（以 - 開頭）

  Rule: 前端應正確渲染 diff 視圖

    Scenario: 使用 Diff2Html 渲染差異
      Given 前端已載入 Diff2Html 函式庫
      When 前端收到 "file_change" 事件
      Then 前端應使用 Diff2Html 渲染 diff
      And 應顯示為 side-by-side 或 line-by-line 格式

    Scenario: diff 視圖應標示新增的行
      Given diff 包含新增的程式碼行
      When 前端渲染 diff
      Then 新增的行應以綠色背景標示
      And 行首應顯示 "+" 符號

    Scenario: diff 視圖應標示刪除的行
      Given diff 包含刪除的程式碼行
      When 前端渲染 diff
      Then 刪除的行應以紅色背景標示
      And 行首應顯示 "-" 符號

    Scenario: diff 視圖應顯示程式碼語法高亮
      Given diff 來自 Python 檔案
      When 前端渲染 diff
      Then 程式碼應套用 Python 語法高亮

  Rule: 多次編輯同一檔案應正確累積顯示

    Scenario: 連續編輯同一檔案
      Given Agent 已編輯 "src/utils.py" 一次
      When Agent 再次編輯 "src/utils.py"
      Then 前端應收到第二個 "file_change" 事件
      And 第二個 diff 應基於第一次編輯後的內容計算

    Scenario: 前端應顯示最新的檔案狀態
      Given Agent 已對 "src/utils.py" 進行多次編輯
      When 使用者查看檔案預覽
      Then 應顯示所有編輯累積後的最終內容

  Rule: 前端應提供檔案瀏覽功能

    Scenario: 顯示 Sandbox 目錄結構
      Given Sandbox 包含多個檔案和資料夾
      When 使用者開啟檔案瀏覽面板
      Then 應顯示 Sandbox 的目錄樹狀結構

    Scenario: 點擊檔案顯示內容
      Given 檔案瀏覽面板已顯示目錄結構
      When 使用者點擊檔案 "src/main.py"
      Then 應在預覽區顯示該檔案的完整內容

    Scenario: 標示已被 Agent 修改的檔案
      Given Agent 已修改 "src/utils.py"
      When 使用者查看檔案瀏覽面板
      Then "src/utils.py" 應有視覺標示表示已修改
