"""
Animated CLI spinner with step tracking and elapsed time.

Shows a spinning animation with a status message and elapsed time,
then resolves to a ✓ or ✗ on completion.

Usage:
    spinner = Spinner()
    spinner.start("Fetching diff...")
    # ... do work ...
    spinner.succeed("Diff fetched")      # ✓ Diff fetched (0.5s)

Or as a context manager:
    with Spinner("Fetching diff...") as s:
        s.update("Blamed 3/5 files...")
"""

from __future__ import annotations

import sys
import threading
import time


class Spinner:
    """An animated CLI spinner with status updates and elapsed time."""

    # Braille dot-dash spinner frames
    _FRAMES = ("⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷")

    def __init__(self, message: str = ""):
        self._message = message
        self._running = False
        self._thread: threading.Thread | None = None
        self._start: float = 0.0
        self._suffix: str = ""

    # ── public API ──────────────────────────────────────────────

    def start(self, message: str = "") -> None:
        """Start the spinner with an optional initial message."""
        if message:
            self._message = message
        self._running = True
        self._start = time.monotonic()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def update(self, message: str, suffix: str = "") -> None:
        """Change the status message shown next to the spinner."""
        self._message = message
        if suffix:
            self._suffix = suffix

    def succeed(self, message: str | None = None) -> None:
        """Stop the spinner and show a green-ish checkmark."""
        self._stop("✓", message or self._message)

    def fail(self, message: str | None = None) -> None:
        """Stop the spinner and show a red-ish cross."""
        self._stop("✗", message or self._message)

    # ── context manager ─────────────────────────────────────────

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.succeed()
        else:
            self.fail()

    # ── internals ───────────────────────────────────────────────

    def _spin(self) -> None:
        idx = 0
        while self._running:
            elapsed = time.monotonic() - self._start
            frame = self._FRAMES[idx % len(self._FRAMES)]
            extra = f" {self._suffix}" if self._suffix else ""
            # \033[K clears to end of line so we overwrite cleanly
            sys.stdout.write(f"\r\033[K{frame} {self._message}{extra}  ")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    def _stop(self, icon: str, message: str) -> None:
        # Idempotent — safe to call multiple times (e.g. explicit fail + __exit__)
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.3)
        elapsed = time.monotonic() - self._start
        sys.stdout.write(f"\r\033[K{icon} {message}  ({elapsed:.1f}s)\n")
        sys.stdout.flush()
