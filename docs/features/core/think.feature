# language: zh-TW
Feature: 思考工具（Think Tool）
  作為 Agent
  我想要在行動前先記錄推理過程
  以便在複雜任務中保持思路清晰並做出更好的決策

  Rule: 應記錄思考內容

    Scenario: 正常思考字串應回傳 recorded
      When Agent 使用 think 工具輸入 "我需要先讀取檔案，再修改程式碼"
      Then 應回傳 status 為 "recorded"
      And 回傳的 thought 應與輸入相同

    Scenario: 空字串應回傳 empty
      When Agent 使用 think 工具輸入空字串
      Then 應回傳 status 為 "empty"
      And thought 應為空字串

    Scenario: 純空白字串應回傳 empty
      When Agent 使用 think 工具輸入 "   \n\t  "
      Then 應回傳 status 為 "empty"
      And thought 應為空字串

    Scenario: 長文字思考應正常記錄
      When Agent 使用 think 工具輸入包含多行步驟的長文字
      Then 應回傳 status 為 "recorded"
      And thought 應完整保留所有內容

  Rule: 應可透過 ToolRegistry 使用

    Scenario: 預設註冊表應包含 think 工具
      Given 使用 create_default_registry 建立工具註冊表
      Then 註冊表中應包含 "think" 工具

    Scenario: 透過 registry 執行 think 工具
      Given 使用 create_default_registry 建立工具註冊表
      When 透過 registry.execute 執行 think 並傳入思考內容
      Then 應回傳 status 為 "recorded"
      And thought 應與輸入相同
