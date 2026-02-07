"""Skill 技能系統。

以 Skill 為單位擴充 Agent 的能力，透過 prompt injection 模組化管理不同領域的指令。
"""

from agent_core.skills.base import Skill
from agent_core.skills.registry import SkillRegistry

__all__ = ['Skill', 'SkillRegistry']
