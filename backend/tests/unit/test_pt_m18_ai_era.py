"""PT-M18's T18, the AI era (the product manager's approval, 2026-11-27): the balance shards
read it a seed at a time (`ptk.balance.ai_era.read_seed`, PT-M14's criteria 2 and 4 as
`tools/tech_readings.py run_seed` reads them) and the summary judges row T18."""

from __future__ import annotations

from ptk.balance.ai_era import AI_ERA, AiEraReading
from ptk.balance.known_misses import verdict
from ptk.balance.report import RunResult, _t18, evaluate, load_shards, runs_table, save_results


def _reading(
    seed: int, saving: float = 0.5, lost: float = 0.6, restored: float = 0.8
) -> AiEraReading:
    untrained = 2.0
    return AiEraReading(seed, saving, untrained + lost, untrained, untrained + restored * lost, 3)


def _row(readings: list[AiEraReading]):  # type: ignore[no-untyped-def]
    (row,) = _t18(readings)
    return row


def test_t18_passes_inside_every_band() -> None:
    row = _row([_reading(s) for s in range(1, 41)])
    assert row.ok and verdict(row) == "ok"
    assert row.value.startswith("50.0%-50.0% (40/40)")


def test_t18_fails_on_one_seed_outside_the_saving_band() -> None:
    readings = [_reading(s) for s in range(1, 40)] + [_reading(40, saving=0.72)]
    assert not _row(readings).ok


def test_t18_reads_medians_of_the_loss_and_the_restored_share() -> None:
    low = [_reading(s, restored=0.4) for s in range(1, 22)]
    high = [_reading(s, restored=0.9) for s in range(22, 41)]
    assert not _row(low + high).ok  # median restored 0.4
    assert _row(low[:19] + high + [_reading(41, restored=0.9)] * 2).ok
    no_loss = [_reading(s, lost=-0.1) for s in range(1, 41)]
    assert not _row(no_loss).ok  # the median loss is not above 0
    assert no_loss[0].restored is None  # a cohort that did not lose has no restored share
    assert AiEraReading(1, 0.5, 1.0, 1.0, 1.0, 0).restored is None  # nor does no cohort


def test_pseudo_runs_reach_only_row_t18(tmp_path) -> None:  # type: ignore[no-untyped-def]
    runs = [
        RunResult(AI_ERA, s, "standard", 360, 1.0, "reading", None, (), 0, 0, None,
                  ai_era=_reading(s))
        for s in (1, 2)
    ]  # fmt: skip
    save_results(tmp_path / "shard-0.pkl", runs)
    loaded = load_shards(tmp_path)
    rows = evaluate(loaded)
    assert [r for r in rows if r.target != "T18"] == evaluate([])  # as with no runs at all
    assert [r.target for r in rows].count("T18") == 1
    assert AI_ERA not in runs_table(loaded)
