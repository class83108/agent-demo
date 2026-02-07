"""Skill Registry 模組。

管理 Skill 的註冊、啟用/停用，以及兩階段 system prompt 合併。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from agent_core.skills.base import Skill

logger = logging.getLogger(__name__)


@dataclass
class SkillRegistry:
    """Skill 註冊表。

    採用兩階段載入策略：
    - Phase 1: 所有 Skill 的 description 注入 system prompt（輕量）
    - Phase 2: 只有啟用的 Skill 才載入完整 instructions
    """

    _skills: dict[str, Skill] = field(default_factory=lambda: {})
    _active: set[str] = field(default_factory=lambda: set())

    def register(self, skill: Skill) -> None:
        """註冊 Skill。

        Args:
            skill: 要註冊的 Skill

        Raises:
            ValueError: Skill 名稱已存在
        """
        if skill.name in self._skills:
            msg = f"Skill '{skill.name}' 已存在，不允許重複註冊"
            raise ValueError(msg)

        self._skills[skill.name] = skill
        logger.info('Skill 已註冊', extra={'skill_name': skill.name})

    def activate(self, name: str) -> None:
        """啟用 Skill（Phase 2 觸發）。

        Args:
            name: Skill 名稱

        Raises:
            KeyError: Skill 不存在
        """
        if name not in self._skills:
            msg = f"Skill '{name}' 不存在"
            raise KeyError(msg)

        self._active.add(name)
        logger.info('Skill 已啟用', extra={'skill_name': name})

    def deactivate(self, name: str) -> None:
        """停用 Skill。

        Args:
            name: Skill 名稱
        """
        self._active.discard(name)
        logger.info('Skill 已停用', extra={'skill_name': name})

    def list_skills(self) -> list[str]:
        """列出所有已註冊的 Skill 名稱。

        Returns:
            Skill 名稱列表
        """
        return list(self._skills.keys())

    def list_active_skills(self) -> list[str]:
        """列出所有已啟用的 Skill 名稱。

        Returns:
            已啟用的 Skill 名稱列表
        """
        return list(self._active)

    def get(self, name: str) -> Skill | None:
        """依名稱取得 Skill。

        Args:
            name: Skill 名稱

        Returns:
            Skill 物件，若不存在則回傳 None
        """
        return self._skills.get(name)

    def get_skill_descriptions(self) -> str:
        """Phase 1: 產生可用 Skill 描述清單。

        只包含 disable_model_invocation 為 False 的 Skill。
        不含完整 instructions。

        Returns:
            Skill 描述清單字串
        """
        visible = [s for s in self._skills.values() if not s.disable_model_invocation]
        if not visible:
            return ''

        lines = ['可用 Skills:']
        for skill in visible:
            lines.append(f'- {skill.name}: {skill.description}')
        return '\n'.join(lines)

    def get_combined_system_prompt(self, base_prompt: str) -> str:
        """合併基礎 prompt、描述清單與已啟用 Skill 的 instructions。

        每次 API call 時呼叫，根據當下狀態重建（stateless）。
        結構：
        1. 基礎 prompt
        2. Phase 1: 所有可見 Skill 的描述清單
        3. Phase 2: 已啟用 Skill 的完整 instructions

        Args:
            base_prompt: 基礎 system prompt

        Returns:
            合併後的 system prompt
        """
        if not self._skills:
            return base_prompt

        parts = [base_prompt]

        # Phase 1: Skill 描述清單
        descriptions = self.get_skill_descriptions()
        if descriptions:
            parts.append(f'\n\n{descriptions}')

        # Phase 2: 已啟用 Skill 的完整 instructions
        for name in self._active:
            skill = self._skills.get(name)
            if skill:
                parts.append(f'\n\n## Skill: {skill.name}\n\n{skill.instructions}')

        return ''.join(parts)
