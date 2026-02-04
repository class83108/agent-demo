# Agent Demo

一個基於 Claude 的 Coding Agent 展示專案，具備工具調用、即時串流回應與沙箱安全機制。

## 核心特色

### Agent 能力

- **工具調用** — 內建 5 種開發工具（檔案讀寫、目錄瀏覽、程式碼搜尋、Bash 執行），每個工具皆有清楚的描述定義，讓 Agent 精準判斷使用時機
- **平行工具執行** — 透過 `asyncio.gather()` 同時執行多個獨立工具，提升回應效率
- **安全限制** — 路徑穿越防護、危險指令阻擋（`rm -rf`、`sudo` 等）、敏感檔案保護（`.env`、私鑰）、輸出內容自動遮蔽 API Key

### Token 利用率

- **Prompt Caching** — System prompt、工具定義與對話歷史皆標記 `cache_control: ephemeral`，快取命中時成本降至 0.1 倍

### UX 提升

- **串流模式** — 透過 SSE（Server-Sent Events）逐 token 即時回傳，搭配 Markdown 渲染與程式碼語法高亮
- **工具執行狀態提示** — 前端即時顯示工具的開始、完成、失敗狀態
- **即時檔案預覽** — Agent 編輯檔案時，前端即時顯示 diff 變更

### 監控

- **Token 使用量追蹤** — 記錄每次請求的 input/output tokens、快取命中率與成本估算

### 開發中功能

- [ ] **Compact** — 對話壓縮功能，降低長對話的 token 消耗
- [ ] **Resume** — 斷線復原架構，客戶端掛掉後可接續上次生成到一半的內容

## 開發流程

本專案採用 **Gherkin 驅動的 TDD 開發流程**，確保每個功能從規格定義到實作皆有明確的驗證依據。

### 1. 撰寫 Gherkin Feature 規格

每個功能在動手寫程式前，先以 Gherkin 語法定義使用情境，放置於 `docs/features/*.feature`。Feature 描述的是 **domain level 的行為**，而非技術實作細節。

```gherkin
# language: zh-TW
Feature: 讀取檔案功能
  作為使用者
  我想要讓 Agent 讀取檔案內容
  以便 Agent 能理解我的程式碼並提供協助

  Rule: Agent 應處理檔案路徑安全性

    Scenario: 阻擋路徑穿越攻擊
      Given 工作目錄為 "/project"
      When 使用者要求讀取 "../../../etc/passwd"
      Then Agent 應拒絕讀取工作目錄外的檔案
      And Agent 應回傳安全性錯誤訊息
```

目前已有的 Feature 規格：

| Feature 檔案 | 涵蓋範圍 |
|---|---|
| `agent_core.feature` | Agent 迴圈、平行工具執行、Prompt Caching |
| `chat.feature` | 對話功能、上下文記憶 |
| `chat_api.feature` | REST API 端點行為 |
| `file_read.feature` | 檔案讀取、安全性防護 |
| `file_edit.feature` | 檔案編輯、原子寫入 |
| `file_list.feature` | 目錄瀏覽 |
| `code_search.feature` | 程式碼搜尋 |
| `bash.feature` | Bash 指令執行、危險指令阻擋 |
| `tool_status.feature` | 工具執行狀態通知 |
| `live_file_preview.feature` | 即時檔案預覽 |

### 2. 紅燈：撰寫 Unit Test

根據 Feature 中的 Scenario 撰寫對應的測試案例（`tests/test_*.py`），測試必須先失敗（紅燈）。

```bash
uv run pytest  # 預期失敗
```

### 3. 綠燈：實作功能

撰寫最小可行程式碼讓測試通過，接著重構優化。

```bash
uv run pytest  # 預期通過
```

### 4. Smoke Test（E2E 驗證）

Smoke test 作為端對端測試，呼叫真實的 Claude API 驗證主要流程可運作。放置於 `tests/manual/`，需要手動觸發。

```bash
export ANTHROPIC_API_KEY=your_api_key
uv run pytest tests/manual --run-smoke -v
```

> **注意：** Smoke test 會產生 API 費用，執行前須設定 `ANTHROPIC_API_KEY` 並加上 `--run-smoke` 參數。

## 程式碼品質與 CI/CD

### 本地工具鏈

| 工具 | 用途 | 指令 |
|------|------|------|
| **Ruff** | Linting + Formatting | `uv run ruff check .` / `uv run ruff format .` |
| **Pyright** | 靜態型別檢查（strict 模式） | `uv run pyright` |
| **pre-commit** | Git commit 前自動執行 Ruff + Pyright | `uv run pre-commit run --all-files` |

### CI/CD Pipeline（GitHub Actions）

| Workflow | 觸發條件 | 內容 |
|----------|----------|------|
| **Code Quality & Tests** | push / PR to `main` | Ruff lint + format check → Pyright → Pytest → Codecov 覆蓋率上傳 |
| **SonarCloud** | push / PR to `main` | 執行測試產生覆蓋率報告 → SonarCloud 靜態分析（程式碼品質、安全性、技術債） |
| **CodeQL** | push / PR to `main` + 每週排程 | GitHub CodeQL 安全性掃描 |

## 技術架構

| 層級 | 技術 |
|------|------|
| Backend | Python 3.12+、FastAPI、Anthropic SDK |
| Frontend | Vanilla JS、SSE、Marked、Highlight.js |
| Session | Redis |
| 套件管理 | uv |
| AI Model | Claude Sonnet 4 |
| 品質工具 | Ruff、Pyright、SonarCloud、CodeQL、Codecov |

## 專案結構

```
agent-demo/
├── src/agent_demo/
│   ├── main.py              # FastAPI 應用程式與 API 路由
│   ├── agent.py             # Agent 核心迴圈
│   ├── session.py           # Redis Session 管理
│   ├── usage_monitor.py     # Token 用量監控
│   ├── types.py             # 型別定義
│   └── tools/               # 工具實作
│       ├── registry.py      # 工具註冊系統
│       ├── bash.py          # Bash 指令執行
│       ├── file_read.py     # 檔案讀取
│       ├── file_edit.py     # 檔案編輯
│       ├── file_list.py     # 目錄瀏覽
│       └── grep_search.py   # 程式碼搜尋
├── static/                  # 前端靜態檔案
├── tests/                   # 測試
├── docs/features/           # Gherkin 功能規格
└── workspace/sandbox/       # Agent 沙箱工作目錄
```

## 快速開始

### 前置需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Redis

### 安裝

```bash
uv sync
```

### 啟動

```bash
export ANTHROPIC_API_KEY=your_api_key
uv run uvicorn agent_demo.main:app --reload --port 8000
```

開啟瀏覽器前往 `http://localhost:8000`。

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/chat/stream` | 串流對話（SSE） |
| GET | `/api/chat/history` | 取得對話歷史 |
| POST | `/api/chat/reset` | 清除對話 |
| GET | `/api/chat/usage` | Token 使用量統計 |
| POST | `/api/chat/usage/reset` | 重置使用量統計 |
| GET | `/api/files/tree` | 沙箱目錄樹 |
| GET | `/api/files/content` | 取得檔案內容 |
| GET | `/health` | 健康檢查 |

## 內建工具

| 工具 | 說明 | 安全限制 |
|------|------|----------|
| `read_file` | 讀取檔案內容，支援語言偵測與行數範圍 | 阻擋 `.env`、憑證檔；上限 1MB |
| `edit_file` | 精確搜尋替換編輯，支援新建檔案 | 原子寫入、備份機制 |
| `list_files` | 遞迴目錄列表，支援 pattern 過濾 | 排除 `node_modules`、`.git` |
| `grep_search` | 正則搜尋程式碼，支援上下文行數 | 結果上限 100 筆 |
| `bash` | 執行 Shell 指令 | 阻擋危險指令；逾時 120s；輸出遮蔽敏感資訊 |

## 開發

```bash
# 測試
uv run pytest

# Lint
uv run ruff check .

# 格式化
uv run ruff format .

# 型別檢查
uv run pyright

# Smoke test（需要 API Key）
uv run pytest tests/manual --run-smoke -v
```

## License

MIT
