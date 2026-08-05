import heapq
import itertools
import threading
from functools import lru_cache

from app.config import get_settings


class QueueTimeoutError(Exception):
    pass


class PriorityConcurrencyLimiter:
    """Caps concurrent LLM calls. Excess callers block on a priority queue
    (lower `priority` served first, FIFO among equal priorities) until a slot
    frees up or `timeout` elapses."""

    def __init__(self, max_concurrent: int) -> None:
        self._max_concurrent = max_concurrent
        self._active = 0
        self._lock = threading.RLock()  # reentrant: acquire()'s timeout path calls release() while holding it
        self._heap: list[tuple[int, int, threading.Event]] = []
        self._counter = itertools.count()

    def acquire(self, priority: int = 5, timeout: float | None = None) -> None:
        with self._lock:
            if self._active < self._max_concurrent:
                self._active += 1
                return
            event = threading.Event()
            entry = (priority, next(self._counter), event)
            heapq.heappush(self._heap, entry)

        acquired = event.wait(timeout)
        if not acquired:
            with self._lock:
                try:
                    self._heap.remove(entry)
                    heapq.heapify(self._heap)
                except ValueError:
                    # A concurrent release() already handed us a slot right as we
                    # timed out; give it straight to the next waiter instead.
                    self.release()
            raise QueueTimeoutError("Timed out waiting for a concurrency slot")

    def release(self) -> None:
        with self._lock:
            if self._heap:
                _, _, event = heapq.heappop(self._heap)
                event.set()  # hand our slot directly to the next waiter
            else:
                self._active -= 1


@lru_cache
def get_concurrency_limiter() -> PriorityConcurrencyLimiter:
    return PriorityConcurrencyLimiter(get_settings().max_concurrent_requests)
