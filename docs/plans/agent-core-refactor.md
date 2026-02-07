# Agent Core 重構規劃書

> 供下一個 agent 接手實作用。請依照 CLAUDE.md 的開發流程：Feature → Test → Code。

---

## 1. 目標

將 `agent-demo` 的核心邏輯抽取為獨立可重用的 `agent-core` 套件，讓使用者能：

- 配置 LLM 模型與 API Key
- 註冊自訂 Skill（一組 tools + system prompt）
- 接入 MCP Server 擴充工具
- 選擇不同的 Session 後端

最終使用範例：

```python
from agent_core import Agent, AgentCoreConfig, ProviderConfig, AnthropicProvider
from agent_core.skills import Skill, ToolDefinition, SkillRegistry

# 配置
config = AgentCoreConfig(
    provider=ProviderConfig(model='claude-haiku-4-20250514', api_key='sk-...'),
    system_prompt='你是一位助手。',
)

# 註冊 Skill
skill_registry = SkillRegistry()
skill_registry.register(my_skill)

# 建立 Agent
tool_registry = ToolRegistry()
skill_registry.register_tools_to(tool_registry)

agent = Agent(
    config=config,
    provider=AnthropicProvider(config.provider),
    tool_registry=tool_registry,
)

async for chunk in agent.chat(messages):
    print(chunk, end="")
```

---

## 2. Feature 檔案拆分

### 現有 Feature 歸屬分析

| 現有檔案 | 歸屬 | 處理方式 |
|----------|------|----------|
| `agent_core.feature` | agent-core | **修改** — 移除 Prompt Caching Rule（移到 provider 層），新增 Provider/Skill 相關 |
| `chat.feature` | agent-core | **修改** — 錯誤類型改為 provider-agnostic |
| `file_read.feature` | agent-core (tools) | **不動** |
| `file_edit.feature` | agent-core (tools) | **不動** |
| `file_list.feature` | agent-core (tools) | **不動** |
| `bash.feature` | agent-core (tools) | **不動** |
| `code_search.feature` | agent-core (tools) | **不動** |
| `chat_api.feature` | agent-demo-app | **不動**（留在 app 層）|
| `tool_status.feature` | agent-demo-app | **不動**（留在 app 層）|
| `live_file_preview.feature` | agent-demo-app | **不動**（留在 app 層）|
| `fitness-tracker-spec.md` | 獨立專案 | **移除或移到別處** |

### 新增 Feature 檔案（agent-core）

需要新增以下 feature 檔案，每個對應一個獨立的業務領域：

#### `docs/features/config.feature` — 配置系統

```gherkin
# language: zh-TW
Feature: Agent 配置系統
  作為開發者
  我想要彈性配置 Agent 的行為
  以便在不同場景使用不同的模型與設定

  Rule: 應支援配置 LLM Provider

    Scenario: 使用預設配置建立 Agent
      Given 未提供任何配置
      When 建立 AgentCoreConfig
      Then Provider 類型應為 "anthropic"
      And 模型應為預設值

    Scenario: 自訂模型與 API Key
      Given 配置指定模型為 "claude-haiku-4-20250514"
      And 配置指定 API Key 為 "sk-test-key"
      When 建立 Agent
      Then Agent 應使用指定的模型
      And Agent 應使用指定的 API Key

    Scenario: API Key 從環境變數讀取
      Given 配置未指定 API Key
      And 環境變數 ANTHROPIC_API_KEY 已設定
      When 建立 AnthropicProvider
      Then Provider 應使用環境變數中的 API Key

  Rule: 應支援配置 System Prompt

    Scenario: 自訂 System Prompt
      Given 配置指定 system_prompt 為 "你是健身教練"
      When Agent 發送 API 請求
      Then 請求的 system prompt 應包含 "你是健身教練"
```

#### `docs/features/provider.feature` — LLM Provider 抽象

```gherkin
# language: zh-TW
Feature: LLM Provider 抽象層
  作為開發者
  我想要可抽換的 LLM Provider
  以便未來支援不同的 AI 模型服務

  Rule: Provider 應封裝 LLM 特定邏輯

    Scenario: Anthropic Provider 串流回應
      Given 已建立 AnthropicProvider
      When 透過 Provider 發送訊息
      Then 應以 AsyncIterator 逐步回傳 token
      And 最終回傳包含 content 和 stop_reason 的結果

    Scenario: Anthropic Provider 處理工具調用
      Given 已建立 AnthropicProvider
      When Claude 回應包含 tool_use block
      Then Provider 應回傳 stop_reason 為 "tool_use"
      And content 應包含 tool_use block 的完整資訊

  Rule: Provider 應轉換特定例外為通用例外

    Scenario: API 金鑰無效
      Given Anthropic API 回傳 AuthenticationError
      When Provider 處理該錯誤
      Then 應拋出 ProviderAuthError

    Scenario: API 連線失敗
      Given Anthropic API 回傳 APIConnectionError
      When Provider 處理該錯誤
      Then 應拋出 ProviderConnectionError

    Scenario: API 回應超時
      Given Anthropic API 回傳 APITimeoutError
      When Provider 處理該錯誤
      Then 應拋出 ProviderTimeoutError

  Rule: Anthropic Provider 應支援 Prompt Caching

    Scenario: 在 system prompt 加上 cache_control
      Given enable_prompt_caching 為 True
      When Provider 建立 API 請求
      Then system prompt 應包含 cache_control ephemeral

    Scenario: 在工具定義最後加上 cache_control
      Given enable_prompt_caching 為 True
      And 有已註冊的工具
      When Provider 建立 API 請求
      Then 最後一個工具定義應包含 cache_control ephemeral

    Scenario: 停用 Prompt Caching
      Given enable_prompt_caching 為 False
      When Provider 建立 API 請求
      Then 不應包含任何 cache_control
```

#### `docs/features/skill.feature` — Skill 系統

```gherkin
# language: zh-TW
Feature: Skill 技能系統
  作為開發者
  我想要以 Skill 為單位擴充 Agent 的能力
  以便模組化管理不同領域的工具與提示

  Rule: Skill 應包含工具與提示

    Scenario: 註冊一個 Skill
      Given 建立包含 2 個 ToolDefinition 的 Skill
      And Skill 包含 system_prompt_addition
      When 將 Skill 註冊到 SkillRegistry
      Then SkillRegistry 應包含該 Skill

    Scenario: Skill 工具註冊到 ToolRegistry
      Given SkillRegistry 包含一個有 3 個工具的 Skill
      When 呼叫 register_tools_to(tool_registry)
      Then ToolRegistry 應包含這 3 個工具
      And 工具的 source 應為 "skill"

    Scenario: 多個 Skill 的工具合併
      Given SkillRegistry 包含 Skill A（2 個工具）和 Skill B（3 個工具）
      When 呼叫 register_tools_to(tool_registry)
      Then ToolRegistry 應包含 5 個工具

  Rule: Skill 應能擴充 System Prompt

    Scenario: 合併基礎提示與 Skill 提示
      Given 基礎 system_prompt 為 "你是一位助手"
      And SkillRegistry 包含 Skill 其 system_prompt_addition 為 "你擅長健身建議"
      When 呼叫 get_combined_system_prompt("你是一位助手")
      Then 結果應包含 "你是一位助手"
      And 結果應包含 "你擅長健身建議"

    Scenario: 無 Skill 時只回傳基礎提示
      Given SkillRegistry 為空
      When 呼叫 get_combined_system_prompt("你是一位助手")
      Then 結果應為 "你是一位助手"

  Rule: Skill 工具名稱不應衝突

    Scenario: 不同 Skill 有相同名稱的工具
      Given Skill A 有工具 "search"
      And Skill B 也有工具 "search"
      When 將兩個 Skill 都註冊到 SkillRegistry
      Then 應拋出 ValueError
      And 錯誤訊息應說明工具名稱衝突
```

#### `docs/features/mcp.feature` — MCP 整合

```gherkin
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
```

#### `docs/features/session.feature` — Session 抽象

```gherkin
# language: zh-TW
Feature: Session 後端抽象
  作為開發者
  我想要可抽換的 Session 後端
  以便在不同環境使用不同的儲存方式

  Rule: 記憶體後端應支援基本操作

    Scenario: 儲存並讀取對話歷史
      Given 使用 MemorySessionBackend
      When 儲存一段對話歷史到 session "abc"
      And 讀取 session "abc" 的歷史
      Then 應回傳相同的對話歷史

    Scenario: 讀取不存在的 session
      Given 使用 MemorySessionBackend
      When 讀取 session "not-exist" 的歷史
      Then 應回傳空列表

    Scenario: 重設 session
      Given 使用 MemorySessionBackend
      And session "abc" 已有對話歷史
      When 重設 session "abc"
      Then 讀取 session "abc" 應回傳空列表

  Rule: Redis 後端應支援持久化

    Scenario: 對話歷史應有 TTL
      Given 使用 RedisSessionBackend 且 TTL 為 86400
      When 儲存一段對話歷史
      Then Redis key 的 TTL 應為 86400 秒
```

### 修改現有 Feature 檔案

#### `agent_core.feature` — 需修改的部分

**移除** "Prompt Caching" Rule（第 80-104 行）→ 移到 `provider.feature`

**新增** 以下 Rule：

```gherkin
  Rule: Agent 應支援透過 Provider 抽象層呼叫 LLM

    Scenario: Agent 使用注入的 Provider
      Given Agent 已配置 AnthropicProvider
      When 使用者發送訊息
      Then Agent 應透過 Provider 發送 API 請求
      And 不應直接使用 anthropic SDK

  Rule: Agent 應整合 Skill 系統

    Scenario: Agent 使用 Skill 的工具
      Given Agent 已載入包含 "record_workout" 工具的 Skill
      When Claude 請求執行 "record_workout"
      Then Agent 應找到並執行該工具

    Scenario: Agent 使用 Skill 的 System Prompt
      Given Agent 基礎 prompt 為 "你是助手"
      And 已載入 Skill 附加 prompt "你擅長健身"
      When Agent 發送 API 請求
      Then system prompt 應同時包含兩段內容
```

#### `chat.feature` — 需修改的部分

**修改** 錯誤處理的 Scenario（第 36-56 行）：
- `API 連線失敗` → 改為 `Provider 連線失敗`，拋出 `ProviderConnectionError`
- `API 金鑰無效` → 改為 `Provider 認證失敗`，拋出 `ProviderAuthError`
- `API 回應超時` → 改為 `Provider 回應超時`，拋出 `ProviderTimeoutError`

---

## 3. 測試對照表

### 現有測試歸屬

| 測試檔案 | 歸屬 | 處理方式 |
|----------|------|----------|
| `test_agent.py` | agent-core | **修改** — mock Provider 而非 anthropic client |
| `test_tool_registry.py` | agent-core | **修改** — 移除 cache_control 斷言 |
| `test_file_read.py` | agent-core | **不動** |
| `test_file_edit.py` | agent-core | **不動** |
| `test_file_list.py` | agent-core | **不動** |
| `test_bash.py` | agent-core | **不動** |
| `test_grep_search.py` | agent-core | **不動** |
| `test_tool_status.py` | agent-demo-app | **不動** |
| `test_api.py` | agent-demo-app | **不動** |
| `manual/test_smoke*.py` | agent-demo-app | **不動** |

### 新增測試

| 新測試檔案 | 對應 Feature |
|-----------|-------------|
| `tests/test_config.py` | `config.feature` |
| `tests/test_anthropic_provider.py` | `provider.feature` |
| `tests/test_skill_registry.py` | `skill.feature` |
| `tests/test_mcp_adapter.py` | `mcp.feature` |
| `tests/test_session_memory.py` | `session.feature` |

---

## 4. 程式碼變更

### 新增檔案

```
src/agent_core/
├── config.py                          # 統一配置
├── providers/
│   ├── __init__.py
│   ├── base.py                        # LLMProvider Protocol, FinalMessage, UsageInfo
│   ├── anthropic_provider.py          # Anthropic 實作（含 cache_control 邏輯）
│   └── exceptions.py                  # ProviderAuthError, ProviderTimeoutError 等
├── skills/
│   ├── __init__.py
│   ├── base.py                        # Skill, ToolDefinition dataclass
│   └── loader.py                      # SkillRegistry
├── mcp/
│   ├── __init__.py
│   ├── client.py                      # MCPClient, MCPServerConfig
│   └── adapter.py                     # MCPToolAdapter
└── session/
    ├── __init__.py
    ├── base.py                        # SessionBackend Protocol
    ├── redis_backend.py               # 現有 session.py 重構
    └── memory_backend.py              # 記憶體版本
```

### 修改檔案

| 檔案 | 變更內容 |
|------|----------|
| `agent.py` | 移除 `import anthropic`；`client: Any` → `provider: LLMProvider`；`_stream_with_tool_loop` 改用 `provider.stream()`；Anthropic 例外處理移到 provider 層 |
| `tools/registry.py` | `Tool` 加 `source` 欄位；`get_tool_definitions()` 移除 `cache_control`（移到 AnthropicProvider） |
| `usage_monitor.py` | 加入多模型定價表 `MODEL_PRICING`；`UsageMonitor.__init__` 接受 `model` 參數 |
| `__init__.py` | 導出公開 API |
| `pyproject.toml` | `name = "agent-core"`；`anthropic` 為核心依賴；`redis`/`mcp` 為 optional |

### 不動的檔案

- `tools/file_read.py`, `file_edit.py`, `file_list.py`, `bash.py`, `grep_search.py`, `path_utils.py`, `setup.py`
- `types.py`

---

## 5. pyproject.toml 變更

```toml
[project]
name = "agent-core"
version = "0.1.0"
description = "可擴充的 AI Agent 核心框架"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.76.0",
]

[project.optional-dependencies]
redis = ["redis>=7.1.0"]
mcp = ["mcp>=1.0.0"]
```

---

## 6. 實作順序

請依照 Feature → Test → Code 的順序執行：

| 步驟 | Feature | 測試 | 程式碼 |
|------|---------|------|--------|
| 1 | `config.feature` | `test_config.py` | `config.py` |
| 2 | `provider.feature` | `test_anthropic_provider.py` | `providers/` |
| 3 | 修改 `agent_core.feature` + `chat.feature` | 修改 `test_agent.py` | 修改 `agent.py` |
| 4 | 修改 `agent_core.feature` (registry) | 修改 `test_tool_registry.py` | 修改 `tools/registry.py` |
| 5 | `skill.feature` | `test_skill_registry.py` | `skills/` |
| 6 | `session.feature` | `test_session_memory.py` | `session/` |
| 7 | `mcp.feature` | `test_mcp_adapter.py` | `mcp/` |
| 8 | — | — | `usage_monitor.py` 修改 |
| 9 | — | — | `__init__.py` + `pyproject.toml` |

---

## 7. 關鍵設計決策

### Provider 抽象

```python
class LLMProvider(Protocol):
    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> AsyncContextManager[StreamResult]: ...
```

- Prompt Caching 邏輯移到 `AnthropicProvider` 內部
- Agent 只看到通用介面，不知道底層是 Anthropic 還是其他
- 例外轉換在 Provider 層完成

### Skill 系統

```python
@dataclass
class Skill:
    name: str
    description: str
    system_prompt_addition: str
    tools: list[ToolDefinition]
```

- 一個 Skill = 一組相關 tools + system prompt 擴充
- Skill 的 tools 註冊到 ToolRegistry 時標記 `source='skill'`
- System prompt 自動合併

### MCP 整合

- MCP 工具註冊到同一個 ToolRegistry，加前綴避免衝突
- Agent 不區分 native/skill/mcp 工具，統一透過 ToolRegistry 執行
- MCP 連線生命週期由應用層管理

### Session 抽象

- `SessionBackend` Protocol 定義介面
- `MemorySessionBackend` 用於開發/測試（不需要 Redis）
- `RedisSessionBackend` 用於生產環境

---

## 8. 驗證方式

1. `uv run pytest` — 所有測試通過
2. `uv run pyright` — 型別檢查通過
3. `uv run ruff check .` — Lint 通過
4. 手動驗證：建立 Agent 對話
5. 手動驗證：註冊 Skill 確認 tools + prompt 合併
6. 手動驗證：`from agent_core import Agent, Skill, ToolRegistry` 可正常導入
