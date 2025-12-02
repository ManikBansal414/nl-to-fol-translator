from __future__ import annotations

import random
import time
from typing import Callable, Iterable


def call_with_backoff(
    fn: Callable[[], object],
    retriable_exceptions: Iterable[type[BaseException]],
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> object:
    delay = base_delay
    retriable = tuple(retriable_exceptions)
    for attempt in range(max_attempts):
        try:
            return fn()
        except retriable as exc:
            if attempt + 1 >= max_attempts:
                raise
            jitter = random.uniform(0.8, 1.2)
            sleep_for = min(delay * jitter, max_delay)
            time.sleep(sleep_for)
            delay = min(delay * 2, max_delay)
        except Exception:
            # Non-retriable errors propagate immediately
            raise
    raise RuntimeError("Exceeded retry attempts")
