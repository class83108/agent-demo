"""T5 — Bug from Symptoms (Hard)。

多檔案電商專案：models/product.py + services/pricing.py + tests/
pricing.py 中計算折扣時用 > 而非 >=，導致「剛好滿 1000 元不打折」。
Agent 收到的只有使用者的症狀描述，需要自行追蹤程式碼定位 bug。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent, MessageParam
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T5 - Bug from Symptoms'
TASK_LEVEL: str = 'hard'
TASK_PROMPT: str = (
    '客戶反映：「我買了總價剛好 1000 元的商品，應該要享有 9 折優惠，'
    '但結帳時顯示原價。超過 1000 元的訂單折扣是正常的。」\n'
    '請找出問題所在並修復，確保測試通過。'
)


def setup(sandbox: Path) -> None:
    """建立多檔案電商專案。"""
    # 建立目錄結構
    (sandbox / 'models').mkdir()
    (sandbox / 'models' / '__init__.py').write_text('', encoding='utf-8')
    (sandbox / 'services').mkdir()
    (sandbox / 'services' / '__init__.py').write_text('', encoding='utf-8')

    # models/product.py
    (sandbox / 'models' / 'product.py').write_text(
        'from __future__ import annotations\n'
        '\n'
        'from dataclasses import dataclass\n'
        '\n'
        '\n'
        '@dataclass\n'
        'class Product:\n'
        '    """商品。"""\n'
        '\n'
        '    name: str\n'
        '    price: float\n'
        '\n'
        '\n'
        '@dataclass\n'
        'class CartItem:\n'
        '    """購物車項目。"""\n'
        '\n'
        '    product: Product\n'
        '    quantity: int\n'
        '\n'
        '    @property\n'
        '    def subtotal(self) -> float:\n'
        '        """小計。"""\n'
        '        return self.product.price * self.quantity\n',
        encoding='utf-8',
    )

    # models/cart.py
    (sandbox / 'models' / 'cart.py').write_text(
        'from __future__ import annotations\n'
        '\n'
        'from models.product import CartItem\n'
        '\n'
        '\n'
        'class Cart:\n'
        '    """購物車。"""\n'
        '\n'
        '    def __init__(self) -> None:\n'
        '        self.items: list[CartItem] = []\n'
        '\n'
        '    def add(self, item: CartItem) -> None:\n'
        '        """加入商品。"""\n'
        '        self.items.append(item)\n'
        '\n'
        '    @property\n'
        '    def total(self) -> float:\n'
        '        """購物車總金額（未折扣）。"""\n'
        '        return sum(item.subtotal for item in self.items)\n',
        encoding='utf-8',
    )

    # services/pricing.py — BUG: 用了 > 而非 >=
    (sandbox / 'services' / 'pricing.py').write_text(
        'from __future__ import annotations\n'
        '\n'
        'from models.cart import Cart\n'
        '\n'
        '# 折扣門檻與折扣率\n'
        'DISCOUNT_THRESHOLD = 1000\n'
        'DISCOUNT_RATE = 0.9  # 9 折\n'
        '\n'
        '\n'
        'def calculate_final_price(cart: Cart) -> float:\n'
        '    """計算最終結帳金額。\n'
        '\n'
        '    滿 DISCOUNT_THRESHOLD 元享有折扣。\n'
        '\n'
        '    Args:\n'
        '        cart: 購物車\n'
        '\n'
        '    Returns:\n'
        '        最終金額\n'
        '    """\n'
        '    total = cart.total\n'
        '    if total > DISCOUNT_THRESHOLD:  # BUG: 應該是 >=\n'
        '        return round(total * DISCOUNT_RATE, 2)\n'
        '    return total\n',
        encoding='utf-8',
    )

    # test_pricing.py
    (sandbox / 'test_pricing.py').write_text(
        'from models.product import Product, CartItem\n'
        'from models.cart import Cart\n'
        'from services.pricing import calculate_final_price\n'
        '\n'
        '\n'
        'def test_no_discount_below_threshold() -> None:\n'
        '    """未滿 1000 元不打折。"""\n'
        '    cart = Cart()\n'
        '    cart.add(CartItem(Product("書", 500), 1))\n'
        '    assert calculate_final_price(cart) == 500\n'
        '\n'
        '\n'
        'def test_discount_above_threshold() -> None:\n'
        '    """超過 1000 元打 9 折。"""\n'
        '    cart = Cart()\n'
        '    cart.add(CartItem(Product("電腦", 1500), 1))\n'
        '    assert calculate_final_price(cart) == 1350.0\n'
        '\n'
        '\n'
        'def test_discount_exactly_at_threshold() -> None:\n'
        '    """剛好 1000 元也應享有 9 折。"""\n'
        '    cart = Cart()\n'
        '    cart.add(CartItem(Product("耳機", 500), 2))\n'
        '    assert calculate_final_price(cart) == 900.0\n'
        '\n'
        '\n'
        'def test_multiple_items() -> None:\n'
        '    """多個商品合計超過門檻。"""\n'
        '    cart = Cart()\n'
        '    cart.add(CartItem(Product("書", 300), 2))\n'
        '    cart.add(CartItem(Product("筆", 500), 1))\n'
        '    # 300*2 + 500 = 1100 -> 1100 * 0.9 = 990\n'
        '    assert calculate_final_price(cart) == 990.0\n',
        encoding='utf-8',
    )


def evaluate(
    sandbox: Path,
    events: list[AgentEvent],
    conversation: list[MessageParam],
) -> EvalResult:
    """評估 bug 修復結果。"""
    details: dict[str, Any] = {}

    pricing_file = sandbox / 'services' / 'pricing.py'
    if not pricing_file.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'services/pricing.py 不存在'},
        )

    content = pricing_file.read_text(encoding='utf-8')
    # 檢查是否修正了比較運算子
    details['has_gte'] = '>=' in content
    details['has_only_gt'] = (
        '> DISCOUNT_THRESHOLD' in content and '>= DISCOUNT_THRESHOLD' not in content
    )

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    # 評分：修正運算子 0.4 + 測試全過 0.6
    score = 0.0
    if details['has_gte'] and not details['has_only_gt']:
        score += 0.4
    if passed:
        score += 0.6

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=score,
        details=details,
    )
