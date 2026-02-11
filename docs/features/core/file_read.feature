# language: zh-TW
Feature: 讀取檔案功能
  作為使用者
  我想要讓 Agent 讀取檔案內容
  以便 Agent 能理解我的程式碼並提供協助

  Background:
    Given Agent 已啟動
    And "read_file" 工具已註冊

  Rule: Agent 應能讀取指定檔案

    Scenario: 讀取存在的文字檔案
      Given 存在檔案 "src/main.py" 包含 Python 程式碼
      When 使用者要求 "請讀取 src/main.py 的內容"
      Then Agent 應調用 "read_file" 工具
      And Agent 應回傳檔案內容
      And 回應應包含檔案的程式碼

    Scenario: 讀取不存在的檔案
      Given 檔案 "nonexistent.py" 不存在
      When 使用者要求 "請讀取 nonexistent.py"
      Then Agent 應調用 "read_file" 工具
      And 工具應回傳檔案不存在的錯誤
      And Agent 應向使用者說明檔案不存在

    Scenario: 讀取空檔案
      Given 存在空檔案 "empty.txt"
      When 使用者要求 "請讀取 empty.txt"
      Then Agent 應調用 "read_file" 工具
      And Agent 應告知使用者檔案為空

  Rule: Agent 應正確處理各種檔案類型

    Scenario: 讀取 Python 檔案
      Given 存在檔案 "example.py"
      When 使用者要求讀取該檔案
      Then Agent 應正確識別為 Python 程式碼
      And 回應應以 Python 語法格式顯示

    Scenario: 讀取 JSON 檔案
      Given 存在檔案 "config.json"
      When 使用者要求讀取該檔案
      Then Agent 應正確識別為 JSON 格式
      And 回應應以 JSON 語法格式顯示

    Scenario: 讀取 Markdown 檔案
      Given 存在檔案 "README.md"
      When 使用者要求讀取該檔案
      Then Agent 應正確識別為 Markdown 格式

    Scenario: 嘗試讀取二進位檔案
      Given 存在二進位檔案 "image.png"
      When 使用者要求讀取該檔案
      Then Agent 應識別為二進位檔案
      And Agent 應告知使用者無法顯示二進位內容

  Rule: Agent 應處理檔案路徑安全性

    Scenario: 使用相對路徑讀取檔案
      Given 工作目錄為 "/project"
      And 存在檔案 "/project/src/main.py"
      When 使用者要求 "請讀取 src/main.py"
      Then Agent 應正確解析相對路徑
      And Agent 應讀取 "/project/src/main.py"

    Scenario: 使用絕對路徑讀取檔案
      Given 存在檔案 "/home/user/project/main.py"
      When 使用者要求讀取 "/home/user/project/main.py"
      Then Agent 應使用絕對路徑讀取檔案

    Scenario: 阻擋路徑穿越攻擊
      Given 工作目錄為 "/project"
      When 使用者要求讀取 "../../../etc/passwd"
      Then Agent 應拒絕讀取工作目錄外的檔案
      And Agent 應回傳安全性錯誤訊息

    Scenario: 阻擋讀取敏感檔案
      When 使用者要求讀取 ".env" 檔案
      Then Agent 應警告該檔案可能包含敏感資訊
      And Agent 應詢問使用者是否確定要讀取

  Rule: Agent 應處理大型檔案

    Scenario: 讀取超過大小限制的檔案
      Given 存在超過 1MB 的大型檔案 "large_file.log"
      When 使用者要求讀取該檔案
      Then Agent 應告知檔案過大
      And Agent 應建議只讀取部分內容

    Scenario: 讀取檔案的指定行數範圍
      Given 存在 1000 行的檔案 "long_file.py"
      When 使用者要求 "請讀取 long_file.py 的第 50 到 100 行"
      Then Agent 應只回傳指定範圍的內容
      And 回應應標示行號
