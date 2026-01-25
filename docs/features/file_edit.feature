# language: zh-TW
Feature: 編輯檔案功能
  作為使用者
  我想要讓 Agent 編輯檔案內容
  以便自動修改程式碼完成開發任務

  Background:
    Given Agent 已啟動
    And "edit_file" 工具已註冊

  Rule: Agent 應能建立新檔案

    Scenario: 建立新的程式檔案
      Given 檔案 "src/new_module.py" 不存在
      When 使用者要求 "建立 src/new_module.py 並加入基本函數"
      Then Agent 應調用 "edit_file" 工具
      And 應建立新檔案 "src/new_module.py"
      And 檔案應包含使用者要求的內容

    Scenario: 建立檔案在不存在的目錄
      Given 目錄 "src/utils/" 不存在
      When 使用者要求建立 "src/utils/helper.py"
      Then Agent 應先建立必要的目錄
      And 應建立新檔案

    Scenario: 拒絕覆蓋已存在的檔案
      Given 檔案 "src/main.py" 已存在
      When 使用者要求建立同名檔案
      Then Agent 應告知檔案已存在
      And Agent 應詢問是否要編輯而非建立

  Rule: Agent 應能編輯現有檔案

    Scenario: 替換檔案中的特定內容
      Given 檔案 "src/main.py" 包含函數 "old_function"
      When 使用者要求 "將 old_function 重新命名為 new_function"
      Then Agent 應使用字串替換方式修改
      And 所有 "old_function" 應被替換為 "new_function"

    Scenario: 在特定位置插入內容
      Given 檔案 "src/main.py" 包含類別定義
      When 使用者要求 "在類別中新增一個方法"
      Then Agent 應在正確位置插入新方法
      And 應保持正確的縮排

    Scenario: 刪除特定內容
      Given 檔案包含已棄用的函數
      When 使用者要求 "刪除 deprecated_function"
      Then Agent 應移除該函數
      And 應保持檔案其餘部分不變

    Scenario: 修改多處相關內容
      Given 檔案中有多處需要修改
      When 使用者描述需要的變更
      Then Agent 應識別所有需要修改的位置
      And Agent 應一次性完成所有修改

  Rule: Agent 應使用精確的編輯方式

    Scenario: 使用 search-replace 模式
      Given 需要替換特定程式碼片段
      When Agent 執行編輯
      Then Agent 應提供要搜尋的原始內容
      And Agent 應提供要替換的新內容
      And 替換應精確匹配

    Scenario: 處理搜尋內容不存在
      Given 檔案不包含要搜尋的內容
      When Agent 嘗試執行替換
      Then 工具應回傳錯誤
      And Agent 應告知使用者找不到要替換的內容

    Scenario: 處理多個匹配
      Given 檔案中有多處匹配搜尋內容
      When Agent 執行替換
      Then Agent 應明確指定要替換的是哪一處
      Or Agent 應詢問使用者要替換哪些

  Rule: Agent 應驗證編輯結果

    Scenario: 編輯後語法檢查
      Given 編輯的是 Python 檔案
      When Agent 完成編輯
      Then Agent 應檢查語法是否正確
      And 若有語法錯誤應立即修復

    Scenario: 編輯後格式檢查
      When Agent 完成編輯
      Then 新增的程式碼應符合專案的格式規範
      And 縮排應與周圍程式碼一致

    Scenario: 顯示編輯差異
      When Agent 完成編輯
      Then Agent 應顯示修改前後的差異
      And 差異應以易讀的格式呈現

  Rule: Agent 應處理編輯安全性

    Scenario: 備份原始檔案
      Given 設定為編輯前備份
      When Agent 編輯檔案
      Then 應先建立原始檔案的備份

    Scenario: 阻擋編輯工作目錄外的檔案
      Given 工作目錄為 "/project"
      When 使用者要求編輯 "/etc/hosts"
      Then Agent 應拒絕編輯
      And Agent 應說明安全性限制

    Scenario: 警告編輯重要設定檔
      When 使用者要求編輯 "pyproject.toml"
      Then Agent 應警告這是重要設定檔
      And Agent 應說明修改的影響

  Rule: Agent 應支援批次編輯

    Scenario: 同時編輯多個檔案
      Given 需要在多個檔案中進行相似修改
      When 使用者要求批次修改
      Then Agent 應識別所有需要修改的檔案
      And Agent 應並行執行編輯

    Scenario: 批次編輯部分失敗
      Given Agent 正在編輯多個檔案
      When 其中一個檔案編輯失敗
      Then Agent 應繼續編輯其他檔案
      And Agent 應報告哪些檔案編輯失敗
