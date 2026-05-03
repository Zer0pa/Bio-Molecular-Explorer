"""Parsl-shaped Runpod dispatcher — simulates GPU job dispatch on CPU.

Real Parsl + Runpod binding will replace this at cutover. The dispatcher
implements the same `DispatchInterface` as `NoOpDispatcher`. The differences:
  - `submit()` returns a handle with `backend="runpod_sim"` (vs "noop")
  - `poll()` reports a progressive status sequence (queued -> running -> done)
  - `wait()` honors the timeout and raises if exceeded

This is sufficient to write tests that look like real GPU dispatch without
actually needing a Runpod connection.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from zer0pa_biomolecular_explorer.orchestration.dispatch import DispatchHandle


@dataclass
class _PendingJob:
    handle: DispatchHandle
    fn: Callable[..., Any]
    args: tuple
    kwargs: dict
    submitted_at: float = field(default_factory=time.perf_counter)
    poll_count: int = 0
    output: Any = None
    error: str | None = None
    finished: bool = False


class RunpodSimDispatcher:
    """Simulates the Runpod GPU dispatch flow on CPU.

    Each submitted job goes through a synthetic queue: poll() returns "queued"
    on the first call, "running" on the second, and "done" on the third.
    Real Runpod has minutes-to-hours latency; the sim runs in milliseconds.

    Same interface as `NoOpDispatcher`; satisfies `DispatchInterface` Protocol.
    """

    def __init__(self, simulated_dispatch_steps: int = 3) -> None:
        self._simulated_dispatch_steps = simulated_dispatch_steps
        self._jobs: dict[str, _PendingJob] = {}
        self._counter = 0

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> DispatchHandle:
        self._counter += 1
        job_id = f"runpod_sim:{self._counter:08d}"
        handle = DispatchHandle(job_id=job_id, backend="runpod_sim")
        self._jobs[job_id] = _PendingJob(
            handle=handle, fn=fn, args=args, kwargs=kwargs
        )
        return handle

    def poll(self, handle: DispatchHandle) -> dict[str, Any]:
        job = self._jobs.get(handle.job_id)
        if job is None:
            return {"status": "error", "output": None, "error": "unknown job"}
        if job.finished:
            return {"status": "done", "output": job.output, "error": job.error}

        job.poll_count += 1
        if job.poll_count == 1:
            return {"status": "queued", "output": None, "error": None}
        if job.poll_count < self._simulated_dispatch_steps:
            return {"status": "running", "output": None, "error": None}

        # Final poll: actually run the function (sim of GPU completion)
        try:
            job.output = job.fn(*job.args, **job.kwargs)
        except Exception as exc:  # noqa: BLE001
            job.error = f"{type(exc).__name__}: {exc}"
            job.finished = True
            return {"status": "error", "output": None, "error": job.error}
        job.finished = True
        return {"status": "done", "output": job.output, "error": None}

    def wait(self, handle: DispatchHandle, timeout_s: float | None = None) -> Any:
        deadline = time.perf_counter() + timeout_s if timeout_s else None
        while True:
            r = self.poll(handle)
            if r["status"] == "done":
                return r["output"]
            if r["status"] == "error":
                raise RuntimeError(r["error"])
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError(f"job {handle.job_id} did not complete in {timeout_s}s")
            # Tight loop is fine in the sim — real Parsl-Runpod has its own backoff
