# language: zh-TW
Feature: 網路搜尋工具（Web Search Tool）
  作為 Agent
  我想要搜尋網路取得最新資訊
  以便回答需要即時知識的問題

  Rule: 應驗證輸入參數

    Scenario: 空查詢應回傳錯誤
      When Agent 使用空字串執行搜尋
      Then 結果應包含 error
      And error 應提示查詢不能為空

    Scenario: 純空白查詢應回傳錯誤
      When Agent 使用純空白字串執行搜尋
      Then 結果應包含 error

    Scenario: 缺少 API key 應回傳錯誤
      When Agent 未設定 API key 並執行搜尋
      Then 結果應包含 error
      And error 應提示未設定 TAVILY_API_KEY

  Rule: 應回傳結構化搜尋結果

    Scenario: 成功搜尋應回傳結構化結果
      Given Tavily API 回傳包含 answer 和 2 筆結果的回應
      When Agent 搜尋 "什麼是 Python"
      Then 結果應包含 query、answer、results
      And result_count 應為 2
      And 每筆結果應包含 title、url、content

    Scenario: API 錯誤應回傳錯誤訊息
      Given Tavily API 拋出 rate limit 例外
      When Agent 執行搜尋
      Then 結果應包含 error
      And error 應包含錯誤類型與訊息

    Scenario: 搜尋結果為空時應正常處理
      Given Tavily API 回傳空結果
      When Agent 執行搜尋
      Then result_count 應為 0
      And results 應為空列表

  Rule: 應可透過 ToolRegistry 使用

    Scenario: 提供 API key 時應包含 web_search 工具
      Given 使用 create_default_registry 建立工具註冊表並提供 tavily_api_key
      Then 註冊表中應包含 "web_search" 工具

    Scenario: 未提供 API key 時不應包含 web_search 工具
      Given 使用 create_default_registry 建立工具註冊表但未提供 tavily_api_key
      Then 註冊表中不應包含 "web_search" 工具
