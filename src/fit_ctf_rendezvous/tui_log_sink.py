"""Thread-safe capture of ``logging`` records for the Textual TUI.

Any thread may emit log records; a ``logging.Handler`` appends formatted lines to a
bounded buffer. The Rendezvous app drains the buffer on the **main thread** via a
short interval timer and calls ``Log.write_line`` — no widget updates off-thread.

Only loggers whose names start with ``fit_ctf`` are forwarded (avoids Textual noise).
"""

from __future__ import annotations

import logging
import threading
from collections import deque


class _FitCtfLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("fit_ctf")


class _TuiBufferHandler(logging.Handler):
    def __init__(self, sink: TuiLogSink) -> None:
        super().__init__()
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with self._sink._lock:
                self._sink._buffer.append(msg)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class TuiLogSink:
    """Buffers ``fit_ctf*`` log lines for draining on the Textual main thread."""

    DEFAULT_MAX_BUFFER_LINES = 5_000
    DEFAULT_DRAIN_CHUNK = 120

    def __init__(
        self,
        *,
        max_buffer_lines: int = DEFAULT_MAX_BUFFER_LINES,
        drain_chunk: int = DEFAULT_DRAIN_CHUNK,
    ) -> None:
        self._drain_chunk = drain_chunk
        self._buffer: deque[str] = deque(maxlen=max_buffer_lines)
        self._lock = threading.Lock()
        self._handler: logging.Handler | None = None

    def attach(self) -> None:
        """Register the TUI buffer handler on the root logger (idempotent)."""
        if self._handler is not None:
            return
        root = logging.getLogger()
        h = _TuiBufferHandler(self)
        h.setLevel(logging.INFO)
        h.addFilter(_FitCtfLogFilter())
        h.setFormatter(logging.Formatter("[%(asctime)s] - %(levelname)s - %(name)s: %(message)s"))
        root.addHandler(h)
        self._handler = h

    def detach(self) -> None:
        """Remove the TUI buffer handler from the root logger."""
        if self._handler is None:
            return
        logging.getLogger().removeHandler(self._handler)
        self._handler = None

    def drain_for_widget(self, max_lines: int | None = None) -> list[str]:
        """Pop up to ``max_lines`` from the buffer (call from the Textual main thread)."""
        limit = self._drain_chunk if max_lines is None else max_lines
        out: list[str] = []
        with self._lock:
            for _ in range(limit):
                if not self._buffer:
                    break
                out.append(self._buffer.popleft())
        return out
