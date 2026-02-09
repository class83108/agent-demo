"""Eval 任務自動探索模組。"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def discover_tasks() -> list[ModuleType]:
    """自動探索所有 eval 任務模組。

    掃描 tests/eval/tasks/ 下所有 t??_*.py 模組，
    並驗證每個模組包含必要的 TASK_NAME、setup、evaluate。

    Returns:
        已匯入的任務模組列表，依模組名排序
    """
    import tests.eval.tasks as tasks_pkg

    modules: list[ModuleType] = []
    for _importer, name, ispkg in pkgutil.iter_modules(tasks_pkg.__path__):
        if not name.startswith('t') or ispkg:
            continue
        mod = importlib.import_module(f'tests.eval.tasks.{name}')
        # 驗證模組符合 EvalTask Protocol
        if hasattr(mod, 'TASK_NAME') and hasattr(mod, 'setup') and hasattr(mod, 'evaluate'):
            modules.append(mod)
    return sorted(modules, key=lambda m: m.__name__)
