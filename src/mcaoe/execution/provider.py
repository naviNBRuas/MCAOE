from __future__ import annotations

import asyncio
from asyncio.subprocess import PIPE
from dataclasses import dataclass, field
from typing import Any
from typing import Protocol
from uuid import UUID, uuid4


@dataclass(slots=True)
class ExecutionTask:
    command: str
    arguments: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    requires_approval: bool = True
    profile: str | None = None
    plugin_name: str | None = None
    risk_level: str = "medium"
    policy_profile: str | None = None
    policy_reason: str | None = None


@dataclass(slots=True)
class ExecutionResult:
    task_id: UUID
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionProvider(Protocol):
    async def execute(self, task: ExecutionTask) -> ExecutionResult:
        """Run a task inside the selected backend."""


class LocalExecutionProvider:
    async def execute(self, task: ExecutionTask) -> ExecutionResult:
        task_id = TaskIdFactory.new_task_id()
        try:
            process = await asyncio.create_subprocess_exec(
                task.command,
                *task.arguments,
                stdout=PIPE,
                stderr=PIPE,
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                task_id=task_id,
                exit_code=127,
                stdout="",
                stderr=str(exc),
                metadata={"command": task.command, "arguments": task.arguments},
            )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=task.timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return ExecutionResult(
                task_id=task_id,
                exit_code=124,
                stdout="",
                stderr=f"Task timed out after {task.timeout_seconds} seconds",
                metadata={"timeout": task.timeout_seconds, "command": task.command},
            )

        return ExecutionResult(
            task_id=task_id,
            exit_code=process.returncode or 0,
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            metadata={"command": task.command, "arguments": task.arguments},
        )


class TaskIdFactory:
    @staticmethod
    def new_task_id() -> UUID:
        return uuid4()
