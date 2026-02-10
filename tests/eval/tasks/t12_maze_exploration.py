"""T12 — Maze Exploration (Special)。

Agent 需要在一個 12 房間的文字迷宮中探索，找出散落在各房間的 5 個密碼片段。
每個房間是 sandbox 中的一個文字檔，內含房間描述、可用出口、以及可能的密碼片段。

測試重點：
- Memory 工具使用（追蹤已探索房間與發現的線索）
- 長對話中的系統化探索（15+ 次工具呼叫）
- Compact 後是否仍能保留關鍵資訊

迷宮結構（12 房間，5 個密碼片段）：
  entrance → great_hall
  great_hall → library [片段1], kitchen (dead end), corridor
  library → study
  study → secret_room [片段2]
  corridor → armory [片段3], chapel
  chapel → tower
  tower → observatory [片段4]
  entrance → garden
  garden → greenhouse
  greenhouse → laboratory [片段5]

最佳路徑：~15 次 read_file（含回溯）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent, MessageParam
from tests.eval.framework import EvalResult

TASK_NAME: str = 'T12 - Maze Exploration'
TASK_LEVEL: str = 'special'
TASK_PROMPT: str = (
    '你面前有一座古老城堡的迷宮。迷宮的入口在 maze/entrance.txt。\n'
    '請使用 read_file 工具探索迷宮中的每個房間，找出散落在各處的密碼片段。\n'
    '密碼由 5 個片段組成，分別藏在不同的房間中。\n\n'
    '建議：\n'
    '- 使用 memory 工具記錄你已探索的房間和發現的線索\n'
    '- 系統化地探索，避免重複訪問\n'
    '- 收集完所有片段後，按順序組合並回報完整密碼\n\n'
    '請找出所有 5 個密碼片段，並回報完整密碼。'
)

# 密碼片段（按順序）
CODE_FRAGMENTS: list[str] = ['OMEGA', 'DELTA', 'SIGMA', 'THETA', 'PHI']

# --- 房間定義 ---

_ROOMS: dict[str, str] = {
    'entrance': (
        '=== 城堡入口 ===\n'
        '\n'
        '你站在一座古老城堡的大門前。厚重的橡木門半開著，\n'
        '石牆上的火把搖曳著微弱的光芒。\n'
        '地面的石板上刻著：「密碼藏於城堡深處，智者方能尋得。」\n'
        '\n'
        '可用出口：\n'
        '  → north: 大廳 (maze/great_hall.txt)\n'
        '  → east:  花園 (maze/garden.txt)\n'
    ),
    'great_hall': (
        '=== 大廳 ===\n'
        '\n'
        '宏偉的大廳，天花板高聳入雲。\n'
        '巨大的水晶吊燈照亮了整個空間。\n'
        '牆上掛著歷代城主的畫像，但沒有任何密碼線索。\n'
        '\n'
        '可用出口：\n'
        '  → south: 入口 (maze/entrance.txt)\n'
        '  → east:  圖書館 (maze/library.txt)\n'
        '  → west:  廚房 (maze/kitchen.txt)\n'
        '  → north: 走廊 (maze/corridor.txt)\n'
    ),
    'library': (
        '=== 圖書館 ===\n'
        '\n'
        '書架從地板一直延伸到天花板，堆滿了古老的典籍。\n'
        '一本攤開的書上用金色墨水寫著：\n'
        '\n'
        '  ╔══════════════════════════╗\n'
        '  ║  密碼第 1 片段：OMEGA    ║\n'
        '  ╚══════════════════════════╝\n'
        '\n'
        '書的下方有一行小字：「第一步已完成，繼續深入探索。」\n'
        '\n'
        '可用出口：\n'
        '  → west:  大廳 (maze/great_hall.txt)\n'
        '  → north: 書房 (maze/study.txt)\n'
    ),
    'study': (
        '=== 書房 ===\n'
        '\n'
        '一間安靜的書房，桌上散落著羊皮紙和墨水瓶。\n'
        '牆角有一扇不起眼的小門，門框上刻著「秘密」二字。\n'
        '書桌上有一張紙條：「真正的寶藏在隱藏的房間裡。」\n'
        '\n'
        '可用出口：\n'
        '  → south: 圖書館 (maze/library.txt)\n'
        '  → east:  密室 (maze/secret_room.txt)\n'
    ),
    'secret_room': (
        '=== 密室 ===\n'
        '\n'
        '一間隱藏的小房間，四周的牆壁上刻滿了古老的符文。\n'
        '房間中央的石碑上發出微弱的藍光：\n'
        '\n'
        '  ╔══════════════════════════╗\n'
        '  ║  密碼第 2 片段：DELTA    ║\n'
        '  ╚══════════════════════════╝\n'
        '\n'
        '石碑底部刻著：「東翼已探索完畢，試試北方的走廊。」\n'
        '\n'
        '可用出口：\n'
        '  → west: 書房 (maze/study.txt)\n'
    ),
    'kitchen': (
        '=== 廚房 ===\n'
        '\n'
        '一間廢棄的廚房，巨大的壁爐已經熄滅多時。\n'
        '架子上還擺著生鏽的鍋碗。桌上有一張發黃的食譜，\n'
        '但與密碼無關。空氣中瀰漫著陳舊的氣味。\n'
        '\n'
        '這是一個死胡同，沒有其他出口。\n'
        '\n'
        '可用出口：\n'
        '  → east: 大廳 (maze/great_hall.txt)\n'
    ),
    'corridor': (
        '=== 走廊 ===\n'
        '\n'
        '一條昏暗的長廊，兩側的盔甲武士靜默佇立。\n'
        '火把的光芒在牆上投射出舞動的影子。\n'
        '走廊分岔成兩條路。\n'
        '\n'
        '可用出口：\n'
        '  → south: 大廳 (maze/great_hall.txt)\n'
        '  → east:  軍械庫 (maze/armory.txt)\n'
        '  → west:  禮拜堂 (maze/chapel.txt)\n'
    ),
    'armory': (
        '=== 軍械庫 ===\n'
        '\n'
        '牆上掛滿了古老的劍、盾和長矛。\n'
        '一面盾牌的背面藏著一張羊皮紙：\n'
        '\n'
        '  ╔══════════════════════════╗\n'
        '  ║  密碼第 3 片段：SIGMA    ║\n'
        '  ╚══════════════════════════╝\n'
        '\n'
        '羊皮紙的邊緣寫著：「勇者之路尚未結束。」\n'
        '\n'
        '可用出口：\n'
        '  → west: 走廊 (maze/corridor.txt)\n'
    ),
    'chapel': (
        '=== 禮拜堂 ===\n'
        '\n'
        '一間莊嚴的禮拜堂，彩色玻璃窗灑下七彩光芒。\n'
        '長椅整齊排列，祭壇上放著一根燭台。\n'
        '沒有密碼線索，但祭壇後方有一扇通往塔樓的門。\n'
        '\n'
        '可用出口：\n'
        '  → east:  走廊 (maze/corridor.txt)\n'
        '  → north: 塔樓 (maze/tower.txt)\n'
    ),
    'tower': (
        '=== 塔樓 ===\n'
        '\n'
        '狹窄的螺旋樓梯通往塔頂。\n'
        '每一層都有小窗戶，可以看到城堡的全景。\n'
        '樓梯頂端有一扇門通往天文台。\n'
        '\n'
        '可用出口：\n'
        '  → south: 禮拜堂 (maze/chapel.txt)\n'
        '  → up:    天文台 (maze/observatory.txt)\n'
    ),
    'observatory': (
        '=== 天文台 ===\n'
        '\n'
        '城堡的最高點，巨大的天文望遠鏡指向星空。\n'
        '星圖上標記著一個特殊的星座，旁邊寫著：\n'
        '\n'
        '  ╔══════════════════════════╗\n'
        '  ║  密碼第 4 片段：THETA    ║\n'
        '  ╚══════════════════════════╝\n'
        '\n'
        '望遠鏡旁的筆記本上寫著：「最後的片段藏在城堡的東邊花園深處。」\n'
        '\n'
        '可用出口：\n'
        '  → down: 塔樓 (maze/tower.txt)\n'
    ),
    'garden': (
        '=== 花園 ===\n'
        '\n'
        '一座被高牆圍繞的花園，但花草早已枯萎。\n'
        '石板小徑蜿蜒穿過荒廢的花圃。\n'
        '噴水池乾涸已久，池底有一些落葉。沒有密碼線索。\n'
        '\n'
        '可用出口：\n'
        '  → west:  入口 (maze/entrance.txt)\n'
        '  → north: 溫室 (maze/greenhouse.txt)\n'
    ),
    'greenhouse': (
        '=== 溫室 ===\n'
        '\n'
        '玻璃屋頂的溫室，裡面竟然還有一些綠色植物存活。\n'
        '空氣溫暖潮濕，藤蔓爬滿了鐵架。\n'
        '角落有一扇通往實驗室的鐵門。\n'
        '\n'
        '可用出口：\n'
        '  → south: 花園 (maze/garden.txt)\n'
        '  → east:  實驗室 (maze/laboratory.txt)\n'
    ),
    'laboratory': (
        '=== 實驗室 ===\n'
        '\n'
        '一間古老的煉金術實驗室，桌上擺滿了試管和蒸餾器。\n'
        '一本實驗筆記的最後一頁寫著：\n'
        '\n'
        '  ╔══════════════════════════╗\n'
        '  ║  密碼第 5 片段：PHI      ║\n'
        '  ╚══════════════════════════╝\n'
        '\n'
        '筆記末尾寫著：「恭喜你找到最後一個片段！\n'
        '完整密碼為五個片段按順序排列：第1-第2-第3-第4-第5。」\n'
        '\n'
        '可用出口：\n'
        '  → west: 溫室 (maze/greenhouse.txt)\n'
    ),
}


def setup(sandbox: Path) -> None:
    """在 sandbox 中建立迷宮房間檔案。"""
    maze_dir = sandbox / 'maze'
    maze_dir.mkdir(exist_ok=True)

    for room_name, content in _ROOMS.items():
        (maze_dir / f'{room_name}.txt').write_text(content, encoding='utf-8')


def evaluate(
    sandbox: Path,
    events: list[AgentEvent],
    conversation: list[MessageParam],
) -> EvalResult:
    """評估 Agent 的迷宮探索結果。"""
    details: dict[str, Any] = {}

    # 收集 agent 最終回覆文字
    final_text = ''
    for event in events:
        if event['type'] == 'text':
            final_text += event.get('data', {}).get('text', '')

    details['final_text_length'] = len(final_text)

    # --- 正確性評分（0.60）：找到密碼片段 ---
    found_fragments: list[str] = []
    for fragment in CODE_FRAGMENTS:
        if fragment in final_text.upper():
            found_fragments.append(fragment)
    details['found_fragments'] = found_fragments
    details['found_count'] = len(found_fragments)

    correctness_score = len(found_fragments) * 0.12  # 每個 0.12，共 0.60

    # --- Memory 使用評分（0.20）：是否使用 memory 工具 ---
    memory_calls = [
        e
        for e in events
        if e['type'] == 'tool_call'
        and e['data'].get('name') == 'memory'
        and e['data'].get('status') == 'completed'
    ]
    memory_count = len(memory_calls)
    details['memory_tool_calls'] = memory_count

    # 使用 memory ≥ 2 次得滿分，1 次得一半
    if memory_count >= 2:
        memory_score = 0.20
    elif memory_count == 1:
        memory_score = 0.10
    else:
        memory_score = 0.0
    details['memory_score'] = memory_score

    # --- 效率評分（0.20）：從 conversation 的 tool_use blocks 取得 read_file 路徑 ---
    visited_rooms: set[str] = set()
    maze_read_count = 0
    total_read_calls = 0

    for msg in conversation:
        if msg['role'] != 'assistant':
            continue
        content = msg['content']
        if not isinstance(content, list):
            continue
        for block in content:
            if block['type'] != 'tool_use':
                continue
            if block['name'] != 'read_file':
                continue
            total_read_calls += 1
            path = str(block['input'].get('path', ''))
            if 'maze/' in path or path.startswith('maze'):
                maze_read_count += 1
                # 取得房間名（maze/xxx.txt → xxx）
                room = path.split('/')[-1].replace('.txt', '')
                visited_rooms.add(room)

    details['maze_read_count'] = maze_read_count
    details['total_read_calls'] = total_read_calls
    details['visited_rooms'] = sorted(visited_rooms)
    details['visited_count'] = len(visited_rooms)

    # 效率：讀取次數越少越好（最佳路徑約 12-15 次）
    if maze_read_count == 0:
        efficiency_score = 0.0
    elif maze_read_count <= 18:
        efficiency_score = 0.20
    elif maze_read_count <= 25:
        efficiency_score = 0.15
    elif maze_read_count <= 35:
        efficiency_score = 0.10
    else:
        efficiency_score = 0.05
    details['efficiency_score'] = efficiency_score

    # 總分
    score = correctness_score + memory_score + efficiency_score
    passed = len(found_fragments) == len(CODE_FRAGMENTS)

    details['correctness_score'] = correctness_score

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=round(score, 2),
        details=details,
    )
