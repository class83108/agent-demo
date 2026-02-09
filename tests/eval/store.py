"""Eval 結果 SQLite 持久化模組。

將每次 eval run 的結果存入 SQLite，支援跨版本查詢與比較。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = 'eval-results/eval.db'


class EvalStore:
    """Eval 結果 SQLite 儲存。

    每次 eval run 建立一筆 run 記錄，每個任務結果存為一筆 result 記錄。
    支援跨版本比較查詢。

    Attributes:
        db_path: SQLite 資料庫路徑
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """初始化 EvalStore。

        Args:
            db_path: SQLite 資料庫路徑，預設為 eval-results/eval.db
        """
        # 自動建立目錄
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        logger.info('EvalStore 已初始化', extra={'db_path': db_path})

    def _init_db(self) -> None:
        """建立資料表（若不存在）。"""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                run_id TEXT PRIMARY KEY,
                agent_version TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                system_prompt_hash TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES eval_runs(run_id),
                task_name TEXT NOT NULL,
                task_level TEXT NOT NULL,
                passed INTEGER NOT NULL,
                score REAL NOT NULL,
                details TEXT,
                tool_calls INTEGER NOT NULL,
                tool_call_sequence TEXT,
                total_tokens INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                ran_verification INTEGER NOT NULL,
                error TEXT
            );
        """)
        self._conn.commit()

    def create_run(
        self,
        agent_version: str,
        system_prompt: str,
        system_prompt_hash: str,
        model: str,
        notes: str | None = None,
    ) -> str:
        """建立新的 eval run 記錄。

        Args:
            agent_version: Agent 版本標記
            system_prompt: 系統提示詞
            system_prompt_hash: 提示詞雜湊值
            model: 使用的模型名稱
            notes: 備註（可選）

        Returns:
            新建立的 run_id (UUID)
        """
        run_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO eval_runs (run_id, agent_version, system_prompt,
                                   system_prompt_hash, model, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, agent_version, system_prompt, system_prompt_hash, model, created_at, notes),
        )
        self._conn.commit()
        logger.info(
            '已建立 eval run',
            extra={'run_id': run_id, 'agent_version': agent_version},
        )
        return run_id

    def save_result(self, run_id: str, result: dict[str, Any]) -> None:
        """儲存單一任務的評估結果。

        Args:
            run_id: 所屬的 run ID
            result: EvalResult.to_dict() 的輸出
        """
        self._conn.execute(
            """
            INSERT INTO eval_results (run_id, task_name, task_level, passed, score,
                                      details, tool_calls, tool_call_sequence,
                                      total_tokens, duration_seconds,
                                      ran_verification, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                result['task_name'],
                result['task_level'],
                int(result['passed']),
                result['score'],
                json.dumps(result.get('details', {}), ensure_ascii=False),
                result['tool_calls'],
                json.dumps(result.get('tool_call_sequence', []), ensure_ascii=False),
                result['total_tokens'],
                result['duration_seconds'],
                int(result['ran_verification']),
                result.get('error'),
            ),
        )
        self._conn.commit()

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        """取得指定 run 的摘要。

        Args:
            run_id: run ID

        Returns:
            包含 run 資訊與各任務結果的摘要字典
        """
        # 取得 run 資訊
        run_row = self._conn.execute(
            'SELECT * FROM eval_runs WHERE run_id = ?',
            (run_id,),
        ).fetchone()
        if run_row is None:
            return {}

        # 取得該 run 的所有結果
        result_rows = self._conn.execute(
            'SELECT * FROM eval_results WHERE run_id = ? ORDER BY task_name',
            (run_id,),
        ).fetchall()

        results = [dict(r) for r in result_rows]
        total = len(results)
        passed = sum(1 for r in results if r['passed'])

        return {
            'run_id': run_id,
            'agent_version': run_row['agent_version'],
            'model': run_row['model'],
            'created_at': run_row['created_at'],
            'notes': run_row['notes'],
            'total_tasks': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': f'{passed}/{total}' if total > 0 else '0/0',
            'avg_score': round(sum(r['score'] for r in results) / total, 2) if total > 0 else 0.0,
            'total_tokens': sum(r['total_tokens'] for r in results),
            'results': results,
        }

    def compare_versions(
        self,
        version_a: str,
        version_b: str,
    ) -> list[dict[str, Any]]:
        """比較兩個 agent 版本的評估結果。

        Args:
            version_a: 第一個版本標記
            version_b: 第二個版本標記

        Returns:
            逐任務比較結果列表
        """
        rows = self._conn.execute(
            """
            SELECT
                COALESCE(a.task_name, b.task_name) as task_name,
                a.passed as a_passed, b.passed as b_passed,
                a.score as a_score, b.score as b_score,
                a.tool_calls as a_tools, b.tool_calls as b_tools,
                a.total_tokens as a_tokens, b.total_tokens as b_tokens
            FROM (
                SELECT e.* FROM eval_results e
                JOIN eval_runs r ON e.run_id = r.run_id
                WHERE r.agent_version = ?
            ) a
            FULL OUTER JOIN (
                SELECT e.* FROM eval_results e
                JOIN eval_runs r ON e.run_id = r.run_id
                WHERE r.agent_version = ?
            ) b ON a.task_name = b.task_name
            ORDER BY task_name
            """,
            (version_a, version_b),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_runs(self) -> list[dict[str, Any]]:
        """列出所有 eval runs。

        Returns:
            run 摘要列表
        """
        rows = self._conn.execute(
            """
            SELECT r.run_id, r.agent_version, r.model, r.created_at, r.notes,
                   COUNT(e.id) as total_tasks,
                   SUM(e.passed) as passed,
                   ROUND(AVG(e.score), 2) as avg_score
            FROM eval_runs r
            LEFT JOIN eval_results e ON r.run_id = e.run_id
            GROUP BY r.run_id
            ORDER BY r.created_at DESC
            """,
        ).fetchall()
        return [dict(r) for r in rows]

    def print_summary(self, run_id: str) -> None:
        """印出格式化的 eval 摘要表格。

        Args:
            run_id: run ID
        """
        summary = self.get_run_summary(run_id)
        if not summary:
            logger.warning('找不到 run', extra={'run_id': run_id})
            return

        # 標題
        lines: list[str] = [
            '',
            '=' * 72,
            f'  Eval Run: {summary["agent_version"]}',
            f'  Model: {summary["model"]}  |  {summary["created_at"]}',
        ]
        if summary.get('notes'):
            lines.append(f'  Notes: {summary["notes"]}')
        lines.extend(
            [
                '=' * 72,
                '',
                f'  {"Task":<35} {"Pass":>6} {"Score":>7} {"Tools":>7} {"Tokens":>8} {"Verify":>8}',
                f'  {"-" * 33} {"-" * 6} {"-" * 7} {"-" * 7} {"-" * 8} {"-" * 8}',
            ]
        )

        for r in summary['results']:
            status = 'PASS' if r['passed'] else 'FAIL'
            verify = 'Yes' if r['ran_verification'] else 'No'
            lines.append(
                f'  {r["task_name"]:<35} {status:>6} {r["score"]:>7.2f}'
                f' {r["tool_calls"]:>7} {r["total_tokens"]:>8} {verify:>8}'
            )

        lines.extend(
            [
                '',
                f'  Pass Rate: {summary["pass_rate"]}  |  Avg Score: {summary["avg_score"]}'
                f'  |  Total Tokens: {summary["total_tokens"]}',
                '=' * 72,
                '',
            ]
        )

        # 用 print 輸出到 pytest 的 captured output
        for line in lines:
            print(line)  # noqa: T201

    def close(self) -> None:
        """關閉資料庫連線。"""
        self._conn.close()
