"""Parsl-shaped dispatch interface.

Real Parsl binds onto `DispatchInterface`. The default `NoOpDispatcher` is for
CPU-side validation: it executes synchronously in-process. The Runpod adapter
will provide a `RunpodDispatcher` that submits jobs to a Runpod GPU pool and
polls for completion — same interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass
class DispatchHandle:
    job_id: str
    backend: str  # "noop" | "runpod" | "parsl_local" | "parsl_hpc"


class DispatchInterface(Protocol):
    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> DispatchHandle:
        ...

    def poll(self, handle: DispatchHandle) -> dict[str, Any]:
        """Return {"status": "pending|done|error", "output": ..., "error": ...}."""
        ...

    def wait(self, handle: DispatchHandle, timeout_s: float | None = None) -> Any:
        ...


class NoOpDispatcher:
    """Synchronous, in-process dispatcher. The submit/wait pair degenerates to
    a direct call. Used to demonstrate that the rest of the pipeline is
    dispatcher-agnostic."""

    def __init__(self) -> None:
        self._results: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> DispatchHandle:
        self._counter += 1
        job_id = f"noop:{self._counter:08d}"
        try:
            output = fn(*args, **kwargs)
            self._results[job_id] = {"status": "done", "output": output, "error": None}
        except Exception as exc:  # noqa: BLE001
            self._results[job_id] = {
                "status": "error",
                "output": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        return DispatchHandle(job_id=job_id, backend="noop")

    def poll(self, handle: DispatchHandle) -> dict[str, Any]:
        return dict(self._results[handle.job_id])

    def wait(self, handle: DispatchHandle, timeout_s: float | None = None) -> Any:
        r = self._results[handle.job_id]
        if r["status"] == "error":
            raise RuntimeError(r["error"])
        return r["output"]
