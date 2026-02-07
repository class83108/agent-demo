"""Agent Core - 可擴充的 AI Agent 核心框架。"""

__version__ = '0.1.0'

from agent_core.agent import Agent
from agent_core.config import AgentCoreConfig, ProviderConfig
from agent_core.providers import AnthropicProvider
from agent_core.skills.base import Skill
from agent_core.skills.registry import SkillRegistry
from agent_core.tools.registry import ToolRegistry

__all__ = [
    'Agent',
    'AgentCoreConfig',
    'AnthropicProvider',
    'ProviderConfig',
    'Skill',
    'SkillRegistry',
    'ToolRegistry',
]
