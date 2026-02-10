# language: zh-TW
Feature: 工作記憶（Memory Tool）
  作為 Agent
  我想要在工作過程中記錄和查閱重要發現
  以便在 context 被壓縮後仍能取回關鍵資訊

  Background:
    Given Memory 工具已啟用並指定記憶目錄

  Rule: 應支援查看記憶目錄與檔案內容

    Scenario: 查看空的記憶目錄
      Given 記憶目錄為空
      When Agent 執行 view 指令且 path 為空
      Then 應回傳目錄內容清單（空）

    Scenario: 查看有檔案的記憶目錄
      Given 記憶目錄中有 "notes.md" 檔案
      When Agent 執行 view 指令且 path 為空
      Then 應回傳包含 "notes.md" 的目錄清單

    Scenario: 查看記憶檔案內容
      Given 記憶目錄中有 "notes.md" 檔案
      When Agent 執行 view 指令且 path 為 "notes.md"
      Then 應回傳檔案內容（含行號格式）

    Scenario: 查看不存在的檔案
      When Agent 執行 view 指令且 path 為 "nonexistent.md"
      Then 應回傳路徑不存在的錯誤訊息

  Rule: 應支援寫入記憶檔案

    Scenario: 建立新的記憶檔案
      When Agent 執行 write 指令建立 "clues.md" 並寫入內容
      Then 檔案應成功建立於記憶目錄中

    Scenario: 覆寫既有的記憶檔案
      Given 記憶目錄中有 "clues.md" 檔案
      When Agent 執行 write 指令覆寫 "clues.md"
      Then 檔案內容應被更新

    Scenario: 寫入巢狀目錄的檔案
      When Agent 執行 write 指令建立 "sub/deep.md"
      Then 應自動建立中間目錄並寫入檔案

  Rule: 應支援刪除記憶檔案

    Scenario: 刪除既有的記憶檔案
      Given 記憶目錄中有 "old.md" 檔案
      When Agent 執行 delete 指令刪除 "old.md"
      Then 檔案應被成功刪除

    Scenario: 刪除不存在的檔案
      When Agent 執行 delete 指令刪除 "nonexistent.md"
      Then 應回傳路徑不存在的錯誤訊息

  Rule: 應防止路徑穿越攻擊

    Scenario: 嘗試存取記憶目錄外的檔案
      When Agent 嘗試 view "../../../etc/passwd"
      Then 應回傳路徑安全錯誤

    Scenario: 嘗試寫入記憶目錄外
      When Agent 嘗試 write "../../evil.sh" 並寫入內容
      Then 應回傳路徑安全錯誤
