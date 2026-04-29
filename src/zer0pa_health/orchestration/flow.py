"""Prefect-shaped flow interface.

Real Prefect binds onto this protocol. Default in-process implementation
provides retry-on-failure, deterministic caching by input hash, and a flat
event log. No Prefect dependency on the originating Mac.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from zer0pa_health.hashing import sha256_of_obj


@dataclass
class FlowStep:
    name: str
    fn: Callable[..., Any]
    max_retries: int = 1
    cache_key: Callable[..., str] | None = None


@dataclass
class FlowResult:
    name: str
    ok: bool
    output: Any
    attempts: int
    elapsed_s: float
    error: str | None = None
    cache_hit: bool = False


class Flow:
    def __init__(self, name: str) -> None:
        self.name = name
        self._cache: dict[str, Any] = {}
        self._log: list[FlowResult] = []

    def run_step(self, step: FlowStep, *args: Any, **kwargs: Any) -> FlowResult:
        cache_key = (
            step.cache_key(*args, **kwargs)
            if step.cache_key is not None
            else sha256_of_obj({"args": args, "kwargs": kwargs})
        )
        if cache_key in self._cache:
            r = FlowResult(
                name=step.name,
                ok=True,
                output=self._cache[cache_key],
                attempts=0,
                elapsed_s=0.0,
                cache_hit=True,
            )
            self._log.append(r)
            return r

        attempts = 0
        last_err: str | None = None
        t0 = time.perf_counter()
        while attempts < step.max_retries:
            attempts += 1
            try:
                output = step.fn(*args, **kwargs)
                self._cache[cache_key] = output
                r = FlowResult(
                    name=step.name,
                    ok=True,
                    output=output,
                    attempts=attempts,
                    elapsed_s=time.perf_counter() - t0,
                )
                self._log.append(r)
                return r
            except Exception as exc:  # noqa: BLE001 (we record and retry)
                last_err = f"{type(exc).__name__}: {exc}"
        r = FlowResult(
            name=step.name,
            ok=False,
            output=None,
            attempts=attempts,
            elapsed_s=time.perf_counter() - t0,
            error=last_err,
        )
        self._log.append(r)
        return r

    @property
    def log(self) -> list[FlowResult]:
        return list(self._log)
