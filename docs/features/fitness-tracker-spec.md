# Fitness Tracker Agent 規格書

## 專案概述

一個基於 Telegram 的個人健身紀錄助手，透過 AI Agent 自然語言介面記錄訓練、追蹤進度、提供健身建議。

### 核心價值

- **低摩擦紀錄**：健身時快速語音/文字輸入，AI 自動解析並儲存
- **個人化分析**：根據你的數據提供進度評估與建議
- **隨時諮詢**：詢問動作、課表、營養等健身問題

---

## 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                         Linode VPS ($5/月)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Server                        │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │  │
│  │  │  Telegram   │───▶│    Agent    │───▶│  Tool Layer  │   │  │
│  │  │   Webhook   │    │   (Haiku)   │    │              │   │  │
│  │  └─────────────┘    └─────────────┘    └──────────────┘   │  │
│  │                            │                   │           │  │
│  │                            ▼                   ▼           │  │
│  │                     ┌─────────────┐    ┌──────────────┐   │  │
│  │                     │ Claude API  │    │  PostgreSQL  │   │  │
│  │                     │ (External)  │    │   (Local)    │   │  │
│  │                     └─────────────┘    └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                │                                    │
                ▼                                    ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│     Modal (Whisper)      │          │    MuscleWiki API        │
│   語音轉文字 (免費額度)    │          │    動作資料庫 (免費)      │
└──────────────────────────┘          └──────────────────────────┘
```

---

## 技術選型

| 元件 | 選擇 | 原因 |
|------|------|------|
| **主機** | Linode Nanode 1GB ($5/月) | 便宜、穩定、足夠跑輕量服務 |
| **語言** | Python 3.12 | 生態系豐富、開發快速 |
| **框架** | FastAPI | 非同步、型別安全、自動文件 |
| **資料庫** | PostgreSQL | 可靠、JSON 支援、免費 |
| **AI 模型** | Claude Haiku (主) / Sonnet (備) | 成本低、能力足夠 |
| **語音轉文字** | Modal + Whisper | $30 免費額度/月 |
| **對外介面** | Telegram Bot API | 官方 API、穩定、支援語音訊息 |
| **動作資料** | MuscleWiki API | 1,700+ 動作、免費、有影片 |

---

## 資料庫設計

### ER Diagram

```
┌─────────────────┐       ┌─────────────────┐
│   user_profile  │       │    exercises    │
├─────────────────┤       ├─────────────────┤
│ telegram_id PK  │       │ id PK           │
│ age             │       │ name            │
│ height_cm       │       │ aliases JSONB   │
│ weight_kg       │       │ muscle_group    │
│ body_fat_pct    │       │ exercise_type   │
│ training_years  │       │ musclewiki_id   │
│ goal            │       │ created_at      │
│ created_at      │       └────────┬────────┘
│ updated_at      │                │
└────────┬────────┘                │
         │                         │
         │    ┌────────────────────┘
         │    │
         ▼    ▼
┌─────────────────────────────────────┐
│           workout_logs              │
├─────────────────────────────────────┤
│ id PK                               │
│ telegram_id FK → user_profile       │
│ exercise_id FK → exercises          │
│ performed_at TIMESTAMP              │
│ sets INT                            │
│ reps INT (nullable)                 │
│ weight_kg FLOAT (nullable)          │
│ duration_sec INT (nullable)         │
│ distance_km FLOAT (nullable)        │
│ rpe INT (nullable)                  │  -- 自覺努力程度 1-10
│ notes TEXT                          │
│ created_at                          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│       strength_standards            │
├─────────────────────────────────────┤
│ id PK                               │
│ exercise_name                       │
│ gender                              │
│ bodyweight_min                      │
│ bodyweight_max                      │
│ level (beginner/intermediate/...)   │
│ one_rep_max_kg                      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│       progress_guidelines           │
├─────────────────────────────────────┤
│ id PK                               │
│ training_years_min                  │
│ training_years_max                  │
│ expected_monthly_gain_pct           │
│ notes                               │
└─────────────────────────────────────┘
```

### SQL Schema

```sql
-- 使用者資料
CREATE TABLE user_profile (
    telegram_id BIGINT PRIMARY KEY,
    age INT,
    height_cm FLOAT,
    weight_kg FLOAT,
    body_fat_pct FLOAT,
    training_years FLOAT DEFAULT 0,
    goal VARCHAR(50),  -- 'bulk', 'cut', 'maintain', 'strength'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 動作庫
CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    aliases JSONB DEFAULT '[]',  -- ["bench press", "臥推", "BP"]
    muscle_group VARCHAR(50),    -- 'chest', 'back', 'legs', 'shoulders', 'arms', 'core'
    exercise_type VARCHAR(20),   -- 'weight', 'bodyweight', 'cardio', 'time'
    musclewiki_id INT,           -- 對應 MuscleWiki API 的 ID
    created_at TIMESTAMP DEFAULT NOW()
);

-- 訓練紀錄
CREATE TABLE workout_logs (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES user_profile(telegram_id),
    exercise_id INT REFERENCES exercises(id),
    performed_at TIMESTAMP DEFAULT NOW(),
    sets INT NOT NULL,
    reps INT,
    weight_kg FLOAT,
    duration_sec INT,
    distance_km FLOAT,
    rpe INT CHECK (rpe >= 1 AND rpe <= 10),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引優化查詢
CREATE INDEX idx_workout_logs_user_date ON workout_logs(telegram_id, performed_at DESC);
CREATE INDEX idx_workout_logs_exercise ON workout_logs(exercise_id);
CREATE INDEX idx_exercises_aliases ON exercises USING GIN(aliases);

-- 力量標準參考表
CREATE TABLE strength_standards (
    id SERIAL PRIMARY KEY,
    exercise_name VARCHAR(100),
    gender VARCHAR(10),
    bodyweight_min FLOAT,
    bodyweight_max FLOAT,
    level VARCHAR(20),  -- 'beginner', 'novice', 'intermediate', 'advanced', 'elite'
    one_rep_max_kg FLOAT
);

-- 進步速度參考
CREATE TABLE progress_guidelines (
    id SERIAL PRIMARY KEY,
    training_years_min FLOAT,
    training_years_max FLOAT,
    expected_monthly_gain_pct FLOAT,
    notes TEXT
);
```

---

## Agent Tools 設計

### Tool 1: `record_workout`

記錄訓練紀錄。

```json
{
    "name": "record_workout",
    "description": "記錄一筆健身訓練紀錄到資料庫",
    "parameters": {
        "type": "object",
        "required": ["exercise_name", "sets"],
        "properties": {
            "exercise_name": {
                "type": "string",
                "description": "動作名稱，會進行模糊比對"
            },
            "sets": {
                "type": "integer",
                "description": "組數"
            },
            "reps": {
                "type": "integer",
                "description": "每組次數（重訓/徒手用）"
            },
            "weight_kg": {
                "type": "number",
                "description": "重量（公斤）"
            },
            "duration_sec": {
                "type": "integer",
                "description": "持續時間（秒，用於計時動作如棒式）"
            },
            "distance_km": {
                "type": "number",
                "description": "距離（公里，用於有氧）"
            },
            "rpe": {
                "type": "integer",
                "description": "自覺努力程度 1-10"
            },
            "notes": {
                "type": "string",
                "description": "備註"
            }
        }
    }
}
```

**實作邏輯：**

```python
async def record_workout(
    telegram_id: int,
    exercise_name: str,
    sets: int,
    reps: int | None = None,
    weight_kg: float | None = None,
    duration_sec: int | None = None,
    distance_km: float | None = None,
    rpe: int | None = None,
    notes: str | None = None,
) -> dict:
    # 1. 模糊比對動作
    exercise = await find_exercise_fuzzy(exercise_name)

    if not exercise:
        return {
            "status": "unknown_exercise",
            "message": f"找不到「{exercise_name}」，請問這是什麼類型的動作？",
            "suggestions": await search_musclewiki(exercise_name)
        }

    # 2. 寫入資料庫
    log = await db.insert_workout_log(
        telegram_id=telegram_id,
        exercise_id=exercise.id,
        sets=sets,
        reps=reps,
        weight_kg=weight_kg,
        duration_sec=duration_sec,
        distance_km=distance_km,
        rpe=rpe,
        notes=notes,
    )

    # 3. 計算額外資訊
    today_volume = await calculate_today_volume(telegram_id, exercise.id)
    last_session = await get_last_session(telegram_id, exercise.id)

    return {
        "status": "success",
        "log_id": log.id,
        "exercise": exercise.name,
        "today_volume_kg": today_volume,
        "comparison": compare_with_last(log, last_session)
    }
```

### Tool 2: `query_workouts`

查詢訓練歷史。

```json
{
    "name": "query_workouts",
    "description": "查詢訓練紀錄",
    "parameters": {
        "type": "object",
        "properties": {
            "exercise_name": {
                "type": "string",
                "description": "特定動作名稱"
            },
            "muscle_group": {
                "type": "string",
                "description": "肌群：chest, back, legs, shoulders, arms, core"
            },
            "days_back": {
                "type": "integer",
                "description": "查詢最近幾天，預設 7"
            },
            "limit": {
                "type": "integer",
                "description": "回傳筆數限制，預設 10"
            }
        }
    }
}
```

### Tool 3: `add_exercise`

新增動作到動作庫。

```json
{
    "name": "add_exercise",
    "description": "新增一個動作到動作庫",
    "parameters": {
        "type": "object",
        "required": ["name", "muscle_group", "exercise_type"],
        "properties": {
            "name": {
                "type": "string",
                "description": "動作正式名稱"
            },
            "aliases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "別名列表"
            },
            "muscle_group": {
                "type": "string",
                "enum": ["chest", "back", "legs", "shoulders", "arms", "core", "cardio"]
            },
            "exercise_type": {
                "type": "string",
                "enum": ["weight", "bodyweight", "cardio", "time"]
            }
        }
    }
}
```

### Tool 4: `get_stats`

取得統計資料。

```json
{
    "name": "get_stats",
    "description": "取得訓練統計與進度分析",
    "parameters": {
        "type": "object",
        "required": ["stat_type"],
        "properties": {
            "stat_type": {
                "type": "string",
                "enum": ["summary", "volume", "frequency", "progress", "pr"],
                "description": "統計類型"
            },
            "exercise_name": {
                "type": "string",
                "description": "特定動作（可選）"
            },
            "period": {
                "type": "string",
                "enum": ["week", "month", "year"],
                "description": "統計週期"
            }
        }
    }
}
```

### Tool 5: `get_user_context`

取得使用者資料與參考基準。

```json
{
    "name": "get_user_context",
    "description": "取得使用者個人資料、力量標準、進步參考值",
    "parameters": {
        "type": "object",
        "properties": {
            "include_profile": {
                "type": "boolean",
                "description": "包含個人資料"
            },
            "include_standards": {
                "type": "boolean",
                "description": "包含力量標準"
            },
            "exercise_name": {
                "type": "string",
                "description": "取得特定動作的標準"
            }
        }
    }
}
```

### Tool 6: `update_profile`

更新個人資料。

```json
{
    "name": "update_profile",
    "description": "更新使用者個人資料",
    "parameters": {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
            "height_cm": {"type": "number"},
            "weight_kg": {"type": "number"},
            "body_fat_pct": {"type": "number"},
            "training_years": {"type": "number"},
            "goal": {
                "type": "string",
                "enum": ["bulk", "cut", "maintain", "strength"]
            }
        }
    }
}
```

### Tool 7: `search_exercise_info`

從 MuscleWiki 搜尋動作資訊。

```json
{
    "name": "search_exercise_info",
    "description": "從 MuscleWiki 搜尋動作資訊，包含教學影片",
    "parameters": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "搜尋關鍵字"
            },
            "muscle": {
                "type": "string",
                "description": "目標肌群篩選"
            },
            "difficulty": {
                "type": "string",
                "enum": ["novice", "intermediate", "advanced"]
            },
            "equipment": {
                "type": "string",
                "description": "器材類型：barbell, dumbbell, bodyweight, cable, machine"
            }
        }
    }
}
```

### Tool 8: `suggest_workout`

建議訓練菜單。

```json
{
    "name": "suggest_workout",
    "description": "根據條件建議訓練動作",
    "parameters": {
        "type": "object",
        "required": ["muscle_groups"],
        "properties": {
            "muscle_groups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "目標肌群列表"
            },
            "available_equipment": {
                "type": "array",
                "items": {"type": "string"},
                "description": "可用器材"
            },
            "exclude_exercises": {
                "type": "array",
                "items": {"type": "string"},
                "description": "排除的動作（如受傷不能做）"
            },
            "difficulty": {
                "type": "string",
                "enum": ["novice", "intermediate", "advanced"]
            }
        }
    }
}
```

---

## System Prompt

```python
SYSTEM_PROMPT = """你是一位專業的健身紀錄助手，幫助使用者記錄訓練、追蹤進度、提供建議。

## 你的職責

1. **記錄訓練**：解析使用者的自然語言輸入，轉換成結構化紀錄
2. **查詢歷史**：提供訓練統計、進度追蹤
3. **提供建議**：根據使用者數據給予個人化建議
4. **動作教學**：透過 MuscleWiki 提供動作資訊與影片

## 輸入解析指南

使用者輸入可能很簡短或不完整：
- "臥推 60 3 10" → 臥推 60kg 3組 10下
- "bp 80 4x8" → Bench Press 80kg 4組 8下
- "跑步 30 分鐘" → 跑步 30 分鐘（有氧）
- "plank 1 分鐘 3 組" → 棒式 60秒 3組

## 回覆原則

- 簡潔有力，不囉唆
- 記錄成功時提供：今日總量、與上次比較
- 使用 emoji 增加可讀性但不過度
- 鼓勵但不浮誇

## 進度評估原則

根據訓練年資調整期望值：
- 新手（<1年）：每月主項可進步 5-10%
- 中手（1-3年）：每月 2-5%
- 進階（3年+）：每月 1-2% 就很好

## 注意事項

- 若動作名稱無法辨識，詢問使用者確認
- 若資料不合理（如臥推 500kg），禮貌確認
- 安全優先：若發現可能的過度訓練或受傷風險，提出警告
"""
```

---

## API Endpoints

```python
# FastAPI 路由設計

# Telegram Webhook
POST /webhook/telegram
    - 接收 Telegram 訊息
    - 處理語音 → 轉文字 → Agent
    - 回傳結果

# Health Check
GET /health
    - 檢查服務狀態
    - 資料庫連線

# 手動 API（備用/除錯）
GET  /api/profile
POST /api/profile
GET  /api/workouts
GET  /api/stats
GET  /api/exercises
```

---

## 成本估算

### 月費預估

| 項目 | 方案 | 費用 |
|------|------|------|
| **Linode VPS** | Nanode 1GB | $5.00 |
| **Modal (Whisper)** | 免費額度 | $0.00 |
| **Claude API** | Haiku 為主 | ~$0.50-2.00 |
| **MuscleWiki API** | 免費 | $0.00 |
| **Telegram** | 免費 | $0.00 |
| **網域（可選）** | 有的話 | ~$1.00 |
| **總計** | | **~$6-8/月** |

### Claude API 細算

假設每月用量：
- 日常記錄：300 則 × Haiku = ~$0.15
- 進階問題：30 則 × Sonnet = ~$0.15
- 總計：~$0.30/月（極度保守估計 $2）

---

## 開發階段

### Phase 1: MVP（預計 1-2 週）

- [ ] 專案初始化（FastAPI + PostgreSQL）
- [ ] Telegram Bot 串接（Webhook 模式）
- [ ] 基本 DB Schema 建立
- [ ] Tool: `record_workout` 實作
- [ ] Tool: `query_workouts` 實作
- [ ] 部署到 Linode

**驗收標準：** 能透過 Telegram 文字記錄訓練並查詢

### Phase 2: 語音支援（預計 1 週）

- [ ] Modal + Whisper 部署
- [ ] Telegram 語音訊息處理
- [ ] 語音 → 文字 → Agent 流程

**驗收標準：** 能用語音記錄訓練

### Phase 3: 進階功能（預計 1-2 週）

- [ ] Tool: `get_stats` 統計分析
- [ ] Tool: `get_user_context` 個人化
- [ ] Tool: `search_exercise_info` MuscleWiki 整合
- [ ] 力量標準表建置
- [ ] 進度評估邏輯

**驗收標準：** 能問「我的臥推進步算快嗎？」並得到合理回答

### Phase 4: 優化（持續）

- [ ] Tool: `suggest_workout` 菜單建議
- [ ] 快捷指令（如 `/stats`）
- [ ] 週報/月報自動推送（排程）
- [ ] 資料匯出功能

---

## 專案結構

```
fitness-tracker/
├── src/
│   └── fitness_tracker/
│       ├── __init__.py
│       ├── main.py              # FastAPI 入口
│       ├── config.py            # 設定管理
│       ├── agent.py             # Agent 核心
│       ├── telegram/
│       │   ├── __init__.py
│       │   ├── webhook.py       # Webhook 處理
│       │   └── handlers.py      # 訊息處理
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py      # Tool 註冊
│       │   ├── record.py        # 記錄相關
│       │   ├── query.py         # 查詢相關
│       │   ├── stats.py         # 統計相關
│       │   └── musclewiki.py    # MuscleWiki 整合
│       ├── db/
│       │   ├── __init__.py
│       │   ├── models.py        # SQLAlchemy Models
│       │   ├── session.py       # DB Session
│       │   └── queries.py       # 常用查詢
│       └── services/
│           ├── __init__.py
│           ├── whisper.py       # Modal Whisper 呼叫
│           └── exercise.py      # 動作模糊比對
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_telegram.py
├── scripts/
│   ├── init_db.py               # 初始化資料庫
│   └── seed_exercises.py        # 匯入基礎動作
├── alembic/                     # DB Migration
│   └── versions/
├── pyproject.toml
├── docker-compose.yml           # 本地開發用
└── README.md
```

---

## 參考資源

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [MuscleWiki API](https://api.musclewiki.com/documentation)
- [Modal Documentation](https://modal.com/docs)
- [Claude API](https://docs.anthropic.com/claude/reference)
- [Strength Standards](https://symmetricstrength.com/)
