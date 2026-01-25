# language: zh-TW
Feature: 程式碼搜尋功能
  作為使用者
  我想要讓 Agent 搜尋程式碼
  以便快速找到特定的函數、類別或程式碼片段

  Background:
    Given Agent 已啟動
    And "grep_search" 工具已註冊

  Rule: Agent 應能搜尋程式碼內容

    Scenario: 搜尋特定字串
      Given 專案中有多個 Python 檔案
      When 使用者要求 "搜尋所有使用 logger 的地方"
      Then Agent 應調用 "grep_search" 工具
      And Agent 應回傳所有包含 "logger" 的程式碼位置

    Scenario: 搜尋函數定義
      When 使用者要求 "找出 process_data 函數在哪裡定義"
      Then Agent 應搜尋 "def process_data"
      And Agent 應回傳函數定義的檔案與行號

    Scenario: 搜尋類別定義
      When 使用者要求 "找出 UserService 類別"
      Then Agent 應搜尋 "class UserService"
      And Agent 應回傳類別定義的位置

    Scenario: 搜尋無結果
      When 使用者搜尋不存在的內容
      Then Agent 應告知找不到匹配結果

  Rule: Agent 應支援正則表達式搜尋

    Scenario: 使用簡單正則表達式
      When 使用者要求 "搜尋所有 TODO 或 FIXME 註解"
      Then Agent 應使用正則表達式 "TODO|FIXME"
      And Agent 應回傳所有匹配結果

    Scenario: 搜尋特定模式的函數
      When 使用者要求 "找出所有 test_ 開頭的函數"
      Then Agent 應使用正則表達式 "def test_\w+"
      And Agent 應回傳所有測試函數

    Scenario: 搜尋特定格式的字串
      When 使用者要求 "找出所有 API endpoint 路徑"
      Then Agent 應使用適當的正則表達式匹配路徑格式
      And Agent 應回傳所有 endpoint 定義

  Rule: Agent 應支援搜尋範圍限制

    Scenario: 限制搜尋特定目錄
      When 使用者要求 "只在 src/ 目錄搜尋"
      Then Agent 應只搜尋 src/ 目錄下的檔案

    Scenario: 限制搜尋特定檔案類型
      When 使用者要求 "只搜尋 Python 檔案"
      Then Agent 應只搜尋 .py 檔案

    Scenario: 排除特定目錄
      When 使用者要求搜尋但排除 tests/ 目錄
      Then Agent 應跳過 tests/ 目錄

    Scenario: 排除常見非程式碼目錄
      When Agent 執行搜尋
      Then 預設應排除 node_modules/, .git/, __pycache__/ 等目錄

  Rule: Agent 應格式化搜尋結果

    Scenario: 顯示匹配行與上下文
      When 搜尋找到匹配結果
      Then 應顯示匹配的檔案路徑
      And 應顯示行號
      And 應顯示匹配行的內容
      And 應高亮匹配的部分

    Scenario: 顯示周圍上下文
      When 使用者要求顯示上下文
      Then 應顯示匹配行的前後各 N 行

    Scenario: 分組顯示結果
      When 搜尋結果來自多個檔案
      Then 結果應按檔案分組顯示

    Scenario: 限制結果數量
      When 搜尋結果過多
      Then Agent 應限制顯示數量
      And Agent 應告知總共找到多少結果

  Rule: Agent 應支援進階搜尋功能

    Scenario: 大小寫不敏感搜尋
      When 使用者要求 "搜尋 config 忽略大小寫"
      Then Agent 應匹配 "config", "Config", "CONFIG" 等

    Scenario: 全詞匹配
      When 使用者要求搜尋完整單詞 "test"
      Then 不應匹配 "testing" 或 "contest"
      And 應只匹配獨立的 "test" 單詞

    Scenario: 搜尋並取得程式碼結構
      When 使用者要求 "找出所有呼叫 api.get 的地方"
      Then Agent 應回傳匹配結果
      And Agent 應說明每個呼叫所在的函數或方法

  Rule: Agent 應優化搜尋效能

    Scenario: 快取搜尋索引
      Given 專案檔案眾多
      When 執行多次搜尋
      Then Agent 應利用快取加速後續搜尋

    Scenario: 處理大型專案
      Given 專案包含數千個檔案
      When 使用者執行搜尋
      Then 搜尋應在合理時間內完成
      And Agent 應告知搜尋進度

    Scenario: 中斷長時間搜尋
      Given 搜尋正在執行中
      When 搜尋時間過長
      Then Agent 應允許使用者中斷搜尋
      And Agent 應回傳已找到的部分結果
