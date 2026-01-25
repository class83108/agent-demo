# language: zh-TW
Feature: Bash 命令執行功能
  作為使用者
  我想要讓 Agent 執行 bash 命令
  以便進行版本控制、測試執行等開發工作

  Background:
    Given Agent 已啟動
    And "bash" 工具已註冊
    And 工作目錄已設定

  Rule: Agent 應能執行基本命令

    Scenario: 執行簡單命令
      When 使用者要求 "執行 git status"
      Then Agent 應調用 "bash" 工具
      And Agent 應回傳命令執行結果

    Scenario: 執行帶參數的命令
      When 使用者要求 "執行 git log --oneline -5"
      Then Agent 應正確傳遞所有參數
      And Agent 應回傳最近 5 個 commit 記錄

    Scenario: 執行管道命令
      When 使用者要求 "執行 cat README.md | head -20"
      Then Agent 應正確處理管道
      And Agent 應回傳前 20 行內容

  Rule: Agent 應正確處理命令輸出

    Scenario: 處理標準輸出
      When 執行成功的命令
      Then Agent 應回傳 stdout 內容

    Scenario: 處理標準錯誤
      When 執行產生錯誤的命令
      Then Agent 應回傳 stderr 內容
      And Agent 應說明命令執行失敗

    Scenario: 處理混合輸出
      When 執行同時產生 stdout 和 stderr 的命令
      Then Agent 應分別標示 stdout 和 stderr

    Scenario: 處理無輸出的命令
      When 執行不產生輸出的命令
      Then Agent 應告知命令已成功執行

    Scenario: 處理大量輸出
      When 執行產生大量輸出的命令
      Then Agent 應截斷過長的輸出
      And Agent 應告知輸出已被截斷

  Rule: Agent 應處理命令執行狀態

    Scenario: 命令執行成功
      When 執行成功的命令
      Then Agent 應回傳 exit code 0
      And Agent 應標示命令成功

    Scenario: 命令執行失敗
      When 執行失敗的命令
      Then Agent 應回傳非零 exit code
      And Agent 應說明失敗原因

    Scenario: 命令執行超時
      Given 設定命令超時為 30 秒
      When 執行耗時超過 30 秒的命令
      Then Agent 應終止該命令
      And Agent 應告知命令執行超時

  Rule: Agent 應確保命令執行安全性

    Scenario: 阻擋危險命令
      When 使用者要求執行 "rm -rf /"
      Then Agent 應拒絕執行
      And Agent 應說明該命令具有危險性

    Scenario: 阻擋系統修改命令
      When 使用者要求執行修改系統設定的命令
      Then Agent 應拒絕執行
      And Agent 應說明安全性考量

    Scenario: 限制命令執行目錄
      Given 工作目錄為 "/project"
      When 使用者要求在 "/etc" 執行命令
      Then Agent 應拒絕執行
      And Agent 應說明只能在工作目錄內執行

    Scenario: 需要確認的命令
      When 使用者要求執行可能有副作用的命令
      Then Agent 應先向使用者說明該命令的影響
      And Agent 應詢問使用者是否確定執行

  Rule: Agent 應支援常見開發命令

    Scenario: 執行 Git 命令
      When 使用者要求 "查看 git 狀態"
      Then Agent 應執行 "git status"
      And Agent 應格式化顯示結果

    Scenario: 執行測試命令
      When 使用者要求 "執行測試"
      Then Agent 應執行 "pytest" 或專案設定的測試命令
      And Agent 應解讀測試結果

    Scenario: 執行套件管理命令
      When 使用者要求 "安裝套件 requests"
      Then Agent 應執行適當的套件安裝命令
      And Agent 應告知安裝結果

    Scenario: 執行 linting 命令
      When 使用者要求 "檢查程式碼風格"
      Then Agent 應執行 linting 工具
      And Agent 應列出發現的問題

  Rule: Agent 應正確處理環境

    Scenario: 使用正確的工作目錄
      Given 工作目錄為 "/project"
      When 執行 "pwd"
      Then 結果應為 "/project"

    Scenario: 存取環境變數
      Given 環境變數 "PROJECT_ENV" 設為 "development"
      When 執行 "echo $PROJECT_ENV"
      Then 結果應包含 "development"

    Scenario: 隔離敏感環境變數
      When 執行可能洩漏 API 金鑰的命令
      Then Agent 應遮蔽敏感資訊
      And 輸出不應包含 API 金鑰
