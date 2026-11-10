"""A reproducible point-in-time comparison using synthetic observations."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from statistics import mean


@dataclass(frozen=True)
class Observation:
    symbol: str
    available_at: datetime
    value: float


@dataclass(frozen=True)
class Forecast:
    cutoff: datetime
    input_hash: str
    values: tuple[tuple[str, float], ...]


def freeze_inputs(observations: tuple[Observation, ...], cutoff: datetime):
    known = sorted(
        (row.symbol, row.available_at.isoformat(), row.value)
        for row in observations
        if row.available_at <= cutoff
    )
    encoded = json.dumps(known, separators=(",", ":"), allow_nan=False).encode()
    return tuple(known), sha256(encoded).hexdigest()


def compare(a: Forecast, b: Forecast, outcomes: tuple[Observation, ...]):
    if (a.cutoff, a.input_hash) != (b.cutoff, b.input_hash):
        raise ValueError("Forecasts must use the same locked input")
    first, second = dict(a.values), dict(b.values)
    actual = {row.symbol: row.value for row in outcomes if row.available_at > a.cutoff}
    forecast_symbols = first.keys() & second.keys()
    common = sorted(forecast_symbols & actual.keys())
    if not common:
        raise ValueError("No shared observations are available")

    return {
        "common_forecast_count": len(forecast_symbols),
        "evaluated_count": len(common),
        "mae_percentage_points": {
            "candidate_a": mean(abs(first[symbol] - actual[symbol]) for symbol in common),
            "candidate_b": mean(abs(second[symbol] - actual[symbol]) for symbol in common),
        },
    }


def main():
    before = datetime.fromisoformat("2024-01-03T13:00:00+00:00")
    cutoff = datetime.fromisoformat("2024-01-03T14:00:00+00:00")
    after = datetime.fromisoformat("2024-01-03T21:00:00+00:00")
    observations = (
        Observation("DEMO-A", before, 1.0),
        Observation("DEMO-B", before, -0.5),
        Observation("DEMO-C", before, 0.2),
        Observation("DEMO-D", after, 99.0),
    )
    snapshot, input_hash = freeze_inputs(observations, cutoff)

    # The offsets are fixtures to make the comparison observable.
    forecast_a = Forecast(cutoff, input_hash, tuple((symbol, value) for symbol, _, value in snapshot))
    forecast_b = Forecast(cutoff, input_hash, tuple((symbol, value + 0.5) for symbol, _, value in snapshot))
    outcomes = (
        Observation("DEMO-A", after, 1.75),
        Observation("DEMO-B", after, -0.25),
    )
    print(json.dumps(compare(forecast_a, forecast_b, outcomes), indent=2))


if __name__ == "__main__":
    main()
