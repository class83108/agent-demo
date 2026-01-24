# Agent Demo 開發規範

## 程式碼風格

### Type Hints
- 所有函數、方法必須使用型別註解
- 使用 `from __future__ import annotations` 啟用延遲評估
- 複雜型別使用 `typing` 模組 (如 `Optional`, `Union`, `TypeVar`)

```python
# 正確
def process_message(content: str, max_tokens: int = 1000) -> dict[str, Any]:
    ...

# 錯誤
def process_message(content, max_tokens=1000):
    ...
```

### 命名規範
- 變數、函數: `snake_case`
- 類別: `PascalCase`
- 常數: `UPPER_SNAKE_CASE`
- 私有成員: `_leading_underscore`

### 註解語言
- 註解以**繁體中文**為主，英文為輔
- Docstring 使用 Google 風格
- 複雜邏輯必須加註解說明意圖

```python
def send_message(content: str) -> Response:
    """發送訊息至 Claude API。

    Args:
        content: 訊息內容

    Returns:
        API 回應物件
    """
    # 檢查訊息長度是否超過限制
    if len(content) > MAX_LENGTH:
        raise ValueError("訊息過長")
```

### Logging
- 禁止使用 `print()` 進行輸出
- 使用 `logging` 模組或 `structlog`
- 日誌等級: DEBUG, INFO, WARNING, ERROR, CRITICAL

```python
import logging

logger = logging.getLogger(__name__)

# 正確
logger.info("處理訊息", extra={"message_id": msg_id})

# 錯誤
print(f"處理訊息: {msg_id}")
```

---

## 開發流程

### 功能開發三步驟

1. **規格文件** (docs/features/)
   - 建立功能規格文件，描述 domain level 的使用情境
   - 包含: 目標、使用者故事、驗收條件

2. **撰寫測試** (Red)
   - 根據規格撰寫測試案例
   - 測試必須先失敗 (紅燈)

3. **實作功能** (Green)
   - 實作最小可行程式碼讓測試通過
   - 重構優化 (Refactor)

### 功能規格範本

```markdown
# 功能名稱

## 目標
簡述此功能要解決的問題

## 使用者故事
作為 [角色]，我想要 [功能]，以便 [價值]

## 情境描述
1. 使用者輸入 ...
2. Agent 接收指令後 ...
3. 系統回應 ...

## 驗收條件
- [ ] 條件一
- [ ] 條件二
```

---

## 專案結構

```
agent-demo/
├── src/
│   └── agent_demo/      # 主程式碼
│       ├── __init__.py
│       ├── agent.py     # Agent 核心
│       └── tools/       # 工具模組
├── tests/               # 測試程式
│   ├── conftest.py
│   └── test_*.py
├── docs/
│   └── features/        # 功能規格文件
└── pyproject.toml
```

---

## 套件管理

使用 **uv** 作為套件管理工具，禁止直接編輯 `pyproject.toml` 的 dependencies。

```bash
# 新增套件
uv add <package>

# 新增開發套件
uv add --dev <package>

# 移除套件
uv remove <package>

# 同步環境
uv sync

# 執行指令
uv run <command>
```

---

## 工具鏈

| 工具 | 用途 | 指令 |
|------|------|------|
| ruff | Linting + Formatting | `uv run ruff check .` / `uv run ruff format .` |
| pyright | Type Checking | `uv run pyright` |
| pytest | 測試 | `uv run pytest` |
| pre-commit | Git Hooks | `uv run pre-commit run --all-files` |

---

## Git 規範

### Commit Message
使用 Conventional Commits 格式:
- `feat:` 新功能
- `fix:` 修復 bug
- `docs:` 文件更新
- `refactor:` 重構
- `test:` 測試相關
- `chore:` 維護工作

### Branch 命名
- `feature/<name>` - 新功能
- `fix/<name>` - 修復
- `refactor/<name>` - 重構
