"""Token/cost capture for eval runs, via the global usage hooks in ai.wrapper."""

from contextlib import contextmanager
from typing import Iterator

from ai.wrapper import UsageRecord, add_usage_hook, remove_usage_hook


class UsageCollector:
    """Accumulates UsageRecords emitted by call_structured while registered."""

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    def __call__(self, record: UsageRecord) -> None:
        self.records.append(record)

    @property
    def tokens_in(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def tokens_out(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def attempts(self) -> int:
        return len(self.records)

    @property
    def failed_attempts(self) -> int:
        return sum(1 for r in self.records if r.status == "failed")


@contextmanager
def collect_usage() -> Iterator[UsageCollector]:
    collector = UsageCollector()
    add_usage_hook(collector)
    try:
        yield collector
    finally:
        remove_usage_hook(collector)
