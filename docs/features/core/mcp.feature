# language: zh-TW
Feature: MCP Server 整合
  作為開發者
  我想要接入 MCP Server 擴充 Agent 的工具
  以便使用外部服務提供的功能

  Rule: 應能連接 MCP Server

    Scenario: 透過 stdio 連接 MCP Server
      Given MCP Server 配置為 stdio 模式
      And command 為 ["node", "server.js"]
      When MCPClient 連接
      Then 連線應成功建立

    Scenario: 連接失敗應拋出錯誤
      Given MCP Server command 不存在
      When MCPClient 嘗試連接
      Then 應拋出 MCPConnectionError

  Rule: 應能探索 MCP Server 的工具

    Scenario: 列出 MCP Server 提供的工具
      Given MCPClient 已連接到提供 2 個工具的 Server
      When 呼叫 list_tools()
      Then 應回傳 2 個工具定義
      And 每個工具應包含 name、description、inputSchema

  Rule: MCP 工具應能註冊到 ToolRegistry

    Scenario: MCP 工具自動加上前綴
      Given MCP Server 名稱為 "weather"
      And Server 提供工具 "get_forecast"
      When MCPToolAdapter 註冊工具到 ToolRegistry
      Then ToolRegistry 應包含 "weather__get_forecast"
      And 工具的 source 應為 "mcp"

    Scenario: 執行 MCP 工具應委派給 Server
      Given ToolRegistry 包含 MCP 工具 "weather__get_forecast"
      When 執行該工具並傳入 {"city": "Taipei"}
      Then 應透過 MCPClient 呼叫 Server 的 "get_forecast"
      And 應回傳 Server 的執行結果

  Rule: MCP 連線生命週期

    Scenario: 關閉連線應清理資源
      Given MCPClient 已連接
      When 呼叫 close()
      Then 子行程應被終止
      And 連線應被關閉
