# language: zh-TW
Feature: 列出檔案功能
  作為使用者
  我想要讓 Agent 列出目錄中的檔案
  以便了解專案結構並找到需要的檔案

  Background:
    Given Agent 已啟動
    And "list_files" 工具已註冊

  Rule: Agent 應能列出目錄內容

    Scenario: 列出目錄中的檔案
      Given 存在目錄 "src/" 包含多個檔案
      When 使用者要求 "請列出 src/ 目錄的檔案"
      Then Agent 應調用 "list_files" 工具
      And Agent 應回傳目錄中的檔案列表

    Scenario: 列出空目錄
      Given 存在空目錄 "empty_dir/"
      When 使用者要求列出該目錄
      Then Agent 應告知目錄為空

    Scenario: 列出不存在的目錄
      Given 目錄 "nonexistent/" 不存在
      When 使用者要求列出該目錄
      Then Agent 應告知目錄不存在

    Scenario: 列出當前工作目錄
      Given 工作目錄包含多個檔案和子目錄
      When 使用者要求 "請列出當前目錄的檔案"
      Then Agent 應列出工作目錄的內容

  Rule: Agent 應支援遞迴列出檔案

    Scenario: 遞迴列出所有檔案
      Given 存在目錄結構:
        | 路徑                    |
        | src/main.py            |
        | src/utils/helper.py    |
        | src/utils/config.py    |
        | tests/test_main.py     |
      When 使用者要求 "請列出專案中所有的 Python 檔案"
      Then Agent 應遞迴搜尋所有子目錄
      And Agent 應回傳所有 .py 檔案的列表

    Scenario: 限制遞迴深度
      Given 存在深層巢狀的目錄結構
      When 使用者要求列出檔案並限制深度為 2
      Then Agent 應只列出 2 層以內的檔案

  Rule: Agent 應支援檔案過濾

    Scenario: 按副檔名過濾
      Given 目錄包含 .py, .js, .md 等多種檔案
      When 使用者要求 "只列出 Python 檔案"
      Then Agent 應只回傳 .py 檔案

    Scenario: 按檔名模式過濾
      Given 目錄包含 test_*.py 和其他檔案
      When 使用者要求 "列出所有測試檔案"
      Then Agent 應回傳符合 test_*.py 模式的檔案

    Scenario: 排除特定目錄
      Given 目錄包含 node_modules/, .git/, src/
      When 使用者要求列出檔案並排除 node_modules
      Then Agent 應不列出 node_modules/ 中的檔案

  Rule: Agent 應正確顯示檔案資訊

    Scenario: 顯示檔案基本資訊
      When 使用者要求列出目錄檔案
      Then 列表應包含檔案名稱
      And 列表應區分檔案與目錄

    Scenario: 顯示詳細檔案資訊
      When 使用者要求 "詳細列出目錄檔案"
      Then 列表應包含檔案大小
      And 列表應包含最後修改時間

    Scenario: 以樹狀結構顯示
      Given 存在多層目錄結構
      When 使用者要求 "以樹狀結構顯示專案"
      Then Agent 應以縮排方式呈現目錄層級

  Rule: Agent 應處理特殊情況

    Scenario: 處理符號連結
      Given 目錄包含符號連結
      When 使用者要求列出檔案
      Then Agent 應標示符號連結
      And Agent 應顯示連結的目標路徑

    Scenario: 處理無權限的目錄
      Given 存在無讀取權限的目錄
      When 使用者要求列出該目錄
      Then Agent 應告知權限不足

    Scenario: 處理隱藏檔案
      Given 目錄包含 .gitignore, .env 等隱藏檔案
      When 使用者要求列出檔案
      Then Agent 預設應不顯示隱藏檔案

    Scenario: 顯示隱藏檔案
      When 使用者要求 "列出所有檔案包含隱藏檔"
      Then Agent 應包含隱藏檔案在列表中
