from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from cortex.contracts.events import Event


@runtime_checkable
class Channel(Protocol):
    """An inbound/outbound surface: Slack, Telegram, email..."""

    name: str

    def emit(self, event: Event) -> None: ...

    def notify(self, message: str, reply_hook: Callable[[str], None] | None = None) -> None: ...
