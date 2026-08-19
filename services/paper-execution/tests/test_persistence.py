from paper_execution.fills import Fill
from paper_execution.orders import PaperOrder
from paper_execution.persistence import insert_fill, insert_paper_order, insert_portfolio_snapshot
from paper_execution.positions import PositionBook


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))


def test_insert_paper_order_issues_expected_sql_and_params():
    cursor = FakeCursor()
    order = PaperOrder(
        order_id="o1",
        strategy_id="s1",
        symbol="BTC-USDT",
        direction="LONG",
        size_pct=0.05,
        risk_decision_code="APPROVE",
        created_at="2026-08-19T00:00:00Z",
    )
    insert_paper_order(cursor, order)

    query, params = cursor.executed[0]
    assert "INSERT INTO paper_orders" in query
    assert params == ("o1", "s1", "BTC-USDT", "LONG", 0.05, "APPROVE", "2026-08-19T00:00:00Z")


def test_insert_fill_issues_expected_sql_and_params():
    cursor = FakeCursor()
    fill = Fill(
        order_id="o1",
        symbol="BTC-USDT",
        direction="LONG",
        size_pct=0.05,
        price=100.1,
        timestamp="t",
    )
    insert_fill(cursor, fill)

    query, params = cursor.executed[0]
    assert "INSERT INTO fills" in query
    assert params == ("o1", "BTC-USDT", "LONG", 0.05, 100.1, "t")


def test_insert_portfolio_snapshot_computes_derived_fields():
    cursor = FakeCursor()
    book = PositionBook()
    book.apply_fill(Fill("o1", "BTC-USDT", "LONG", 0.05, 100.0, "t"))

    insert_portfolio_snapshot(
        cursor,
        equity=100_000.0,
        realized_pnl_total=0.0,
        book=book,
        current_prices={"BTC-USDT": 110.0},
        timestamp="2026-08-19T00:00:00Z",
    )

    query, params = cursor.executed[0]
    assert "INSERT INTO portfolio_snapshots" in query
    equity, realized, unrealized, gross, net, positions_json, timestamp = params
    assert equity == 100_000.0
    assert unrealized == 0.5  # 0.05 * (110 - 100)
    assert gross == 0.05
    assert net == 0.05
    assert '"netSize": 0.05' in positions_json
    assert timestamp == "2026-08-19T00:00:00Z"
