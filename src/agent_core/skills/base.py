"""Skill 基礎定義。

定義 Skill 資料結構，一個 Skill 是一組 prompt 指令的封裝。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    """技能定義。

    一個 Skill 代表一組 prompt 指令，採用兩階段載入：
    - Phase 1: name + description 注入 system prompt，讓 LLM 知道可用
    - Phase 2: 啟用後才載入完整 instructions

    Attributes:
        name: 技能名稱（唯一識別）
        description: 技能描述（Phase 1，每次 API call 都帶）
        instructions: 完整指令（Phase 2，啟用後才注入）
        disable_model_invocation: 若為 True，Phase 1 也不載入描述
    """

    name: str
    description: str
    instructions: str
    disable_model_invocation: bool = False
