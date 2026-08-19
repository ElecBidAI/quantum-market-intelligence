import pytest

from paper_execution.fills import Fill
from paper_execution.positions import PositionBook, reconcile, replay_positions


def make_fill(direction, size_pct, price):
    return Fill(
        order_id="o",
        symbol="BTC-USDT",
        direction=direction,
        size_pct=size_pct,
        price=price,
        timestamp="t",
    )


class TestPositionBookLifecycle:
    """Hand-traced: open -> add -> partial close -> flip (see commit context for the trace)."""

    def test_open_new_position(self):
        book = PositionBook()
        book.apply_fill(make_fill("LONG", 0.05, 100.0))
        pos = book.positions["BTC-USDT"]
        assert pos.net_size == pytest.approx(0.05)
        assert pos.avg_entry_price == pytest.approx(100.0)

    def test_adding_to_a_position_averages_the_entry_price(self):
        book = PositionBook()
        book.apply_fill(make_fill("LONG", 0.05, 100.0))
        book.apply_fill(make_fill("LONG", 0.05, 110.0))
        pos = book.positions["BTC-USDT"]
        assert pos.net_size == pytest.approx(0.10)
        assert pos.avg_entry_price == pytest.approx(105.0)

    def test_partial_close_realizes_pnl_on_the_closed_portion_only(self):
        book = PositionBook()
        book.apply_fill(make_fill("LONG", 0.05, 100.0))
        book.apply_fill(make_fill("LONG", 0.05, 110.0))
        book.apply_fill(make_fill("SHORT", 0.06, 120.0))

        pos = book.positions["BTC-USDT"]
        assert pos.net_size == pytest.approx(0.04)
        assert pos.avg_entry_price == pytest.approx(105.0)  # unchanged by a closing fill
        assert book.realized_pnl_total == pytest.approx(0.9)
        assert book.closed_trade_returns == pytest.approx([0.14285714285714285])

    def test_flip_closes_the_remainder_and_opens_the_opposite_side(self):
        book = PositionBook()
        book.apply_fill(make_fill("LONG", 0.05, 100.0))
        book.apply_fill(make_fill("LONG", 0.05, 110.0))
        book.apply_fill(make_fill("SHORT", 0.06, 120.0))
        book.apply_fill(make_fill("SHORT", 0.08, 90.0))

        pos = book.positions["BTC-USDT"]
        assert pos.net_size == pytest.approx(-0.04)
        assert pos.avg_entry_price == pytest.approx(90.0)  # reset to the flip's fill price
        assert book.realized_pnl_total == pytest.approx(0.3)
        assert book.closed_trade_returns == pytest.approx(
            [0.14285714285714285, -0.14285714285714285]
        )

    def test_fully_closing_a_position_removes_it_from_the_book(self):
        book = PositionBook()
        book.apply_fill(make_fill("LONG", 0.05, 100.0))
        book.apply_fill(make_fill("SHORT", 0.05, 110.0))
        assert "BTC-USDT" not in book.positions


def test_unrealized_pnl_long_and_short():
    book = PositionBook()
    book.apply_fill(make_fill("LONG", 0.05, 100.0))
    assert book.positions["BTC-USDT"].unrealized_pnl(110.0) == pytest.approx(0.5)
    assert book.positions["BTC-USDT"].unrealized_pnl(90.0) == pytest.approx(-0.5)


def test_gross_and_net_exposure():
    book = PositionBook()
    book.apply_fill(make_fill("LONG", 0.05, 100.0))
    book.apply_fill(Fill("o", "ETH-USDT", "SHORT", 0.03, 50.0, "t"))
    assert book.gross_exposure_pct() == pytest.approx(0.08)
    assert book.net_exposure_pct() == pytest.approx(0.02)


def test_apply_fill_rejects_non_positive_price():
    book = PositionBook()
    with pytest.raises(ValueError):
        book.apply_fill(make_fill("LONG", 0.05, 0))


class TestReconciliation:
    def test_a_correctly_maintained_book_has_no_discrepancies(self):
        fills = [make_fill("LONG", 0.05, 100.0), make_fill("LONG", 0.05, 110.0)]
        live_book = PositionBook()
        for fill in fills:
            live_book.apply_fill(fill)

        assert reconcile(live_book, fills) == []

    def test_a_missed_fill_is_caught_as_a_discrepancy(self):
        fills = [make_fill("LONG", 0.05, 100.0), make_fill("LONG", 0.05, 110.0)]
        live_book = PositionBook()
        live_book.apply_fill(fills[0])  # "forgets" to apply the second fill

        discrepancies = reconcile(live_book, fills)

        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == "BTC-USDT"
        assert discrepancies[0].live_net_size == pytest.approx(0.05)
        assert discrepancies[0].replayed_net_size == pytest.approx(0.10)

    def test_replay_positions_matches_incremental_application(self):
        fills = [
            make_fill("LONG", 0.05, 100.0),
            make_fill("LONG", 0.05, 110.0),
            make_fill("SHORT", 0.06, 120.0),
        ]
        replayed = replay_positions(fills)
        assert replayed.positions["BTC-USDT"].net_size == pytest.approx(0.04)
