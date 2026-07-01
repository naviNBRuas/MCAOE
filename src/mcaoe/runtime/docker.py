from __future__ import annotations

import asyncio
import logging
import shutil
from asyncio.subprocess import PIPE
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcaoe.execution.provider import ExecutionResult, ExecutionTask

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RuntimeStatus:
    image: str
    healthy: bool
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "image": self.image,
            "healthy": self.healthy,
            "message": self.message,
        }


@dataclass(slots=True)
class DockerSecurityProfile:
    name: str
    network_mode: str = "bridge"
    read_only_rootfs: bool = False
    memory_limit: str = "1g"
    cpus: str = "1.5"
    pids_limit: int = 256
    no_new_privileges: bool = True


SECURITY_PROFILES: dict[str, DockerSecurityProfile] = {
    "recon_standard": DockerSecurityProfile(
        name="recon_standard",
        network_mode="bridge",
        read_only_rootfs=False,
        memory_limit="1g",
        cpus="1.5",
        pids_limit=256,
        no_new_privileges=True,
    ),
    "defensive_strict": DockerSecurityProfile(
        name="defensive_strict",
        network_mode="none",
        read_only_rootfs=True,
        memory_limit="768m",
        cpus="1.0",
        pids_limit=128,
        no_new_privileges=True,
    ),
}


@dataclass(slots=True)
class DockerRuntimeManager:
    image: str = "blackarchlinux/blackarch"
    container_name_prefix: str = "mcaoe"
    docker_executable: str = "docker"
    container_cleanup: bool = True

    async def ensure_runtime(self) -> dict[str, Any]:
        return self.status().as_dict()

    def status(self) -> RuntimeStatus:
        docker_path = shutil.which(self.docker_executable)
        if docker_path is None:
            return RuntimeStatus(
                image=self.image,
                healthy=False,
                message=f"Docker executable {self.docker_executable!r} was not found on PATH.",
            )
        return RuntimeStatus(
            image=self.image,
            healthy=True,
            message=f"Docker runtime is available via {docker_path}.",
        )

    def describe(self) -> dict[str, str]:
        return {
            "image": self.image,
            "container_name_prefix": self.container_name_prefix,
            "docker_executable": self.docker_executable,
            "status": self.status().message,
        }

    def _select_security_profile(self, task: ExecutionTask) -> DockerSecurityProfile:
        profile = (task.policy_profile or task.profile or "").lower()
        if profile in {"dfir", "threat_hunting"}:
            return SECURITY_PROFILES["defensive_strict"]
        return SECURITY_PROFILES["recon_standard"]

    def _build_command(self, task: ExecutionTask) -> tuple[list[str], str]:
        workdir = Path.cwd()
        container_name = f"{self.container_name_prefix}-{uuid4().hex[:8]}"
        security = self._select_security_profile(task)
        security_flags: list[str] = [
            "--network",
            security.network_mode,
            "--memory",
            security.memory_limit,
            "--cpus",
            security.cpus,
            "--pids-limit",
            str(security.pids_limit),
        ]
        if security.no_new_privileges:
            security_flags.extend(["--security-opt", "no-new-privileges"])
        if security.read_only_rootfs:
            security_flags.append("--read-only")

        command: list[str] = [
            self.docker_executable,
            "run",
            "--rm",
            "--name",
            container_name,
            *security_flags,
            "-v",
            f"{workdir}:{workdir}",
            "-w",
            str(workdir),
            self.image,
            task.command,
            *task.arguments,
        ]
        return command, container_name

    async def stop_container(self, container_name: str, timeout: int = 10) -> None:
        docker_path = shutil.which(self.docker_executable)
        if docker_path is None:
            return
        try:
            stop_proc = await asyncio.create_subprocess_exec(
                docker_path, "stop", "--time", str(timeout), container_name,
                stdout=PIPE, stderr=PIPE,
            )
            await stop_proc.communicate()
        except Exception:
            logger.exception("Failed to stop container %s", container_name)
        if self.container_cleanup:
            try:
                rm_proc = await asyncio.create_subprocess_exec(
                    docker_path, "rm", "--force", container_name,
                    stdout=PIPE, stderr=PIPE,
                )
                await rm_proc.communicate()
            except Exception:
                logger.exception("Failed to remove container %s", container_name)

    async def stream_logs(
        self,
        task: ExecutionTask,
        on_line: Callable[[str], None] | None = None,
    ) -> ExecutionResult:
        task_id = uuid4()
        docker_path = shutil.which(self.docker_executable)
        security = self._select_security_profile(task)
        if docker_path is None:
            return ExecutionResult(
                task_id=task_id,
                exit_code=127,
                stderr=f"Docker executable {self.docker_executable!r} was not found on PATH.",
                metadata={"backend": "docker", "image": self.image, "security_profile": security.name},
            )

        command, container_name = self._build_command(task)
        command[0] = docker_path

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=PIPE,
                stderr=PIPE,
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                task_id=task_id,
                exit_code=127,
                stderr=str(exc),
                metadata={
                    "backend": "docker",
                    "image": self.image,
                    "command": task.command,
                    "security_profile": security.name,
                },
            )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def _read_stream(
            stream: asyncio.StreamReader | None,
            lines: list[str],
        ) -> None:
            if stream is None:
                return
            while True:
                raw = await stream.readline()
                if not raw:
                    break
                decoded = raw.decode(errors="replace").rstrip("\n")
                lines.append(decoded)
                if on_line is not None:
                    on_line(decoded)

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    _read_stream(process.stdout, stdout_lines),
                    _read_stream(process.stderr, stderr_lines),
                ),
                timeout=task.timeout_seconds,
            )
        except asyncio.TimeoutError:
            await self.stop_container(container_name)
            return ExecutionResult(
                task_id=task_id,
                exit_code=124,
                stderr=f"Task timed out after {task.timeout_seconds} seconds",
                metadata={
                    "backend": "docker",
                    "image": self.image,
                    "timeout": task.timeout_seconds,
                    "security_profile": security.name,
                },
            )

        await process.wait()
        return ExecutionResult(
            task_id=task_id,
            exit_code=process.returncode or 0,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
            metadata={
                "backend": "docker",
                "image": self.image,
                "command": task.command,
                "arguments": task.arguments,
                "security_profile": security.name,
                "container": container_name,
            },
        )

    async def run(self, task: ExecutionTask) -> ExecutionResult:
        task_id = uuid4()
        docker_path = shutil.which(self.docker_executable)
        security = self._select_security_profile(task)
        if docker_path is None:
            return ExecutionResult(
                task_id=task_id,
                exit_code=127,
                stderr=f"Docker executable {self.docker_executable!r} was not found on PATH.",
                metadata={"backend": "docker", "image": self.image, "security_profile": security.name},
            )

        command, container_name = self._build_command(task)
        command[0] = docker_path

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=PIPE,
                stderr=PIPE,
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                task_id=task_id,
                exit_code=127,
                stderr=str(exc),
                metadata={
                    "backend": "docker",
                    "image": self.image,
                    "command": task.command,
                    "security_profile": security.name,
                },
            )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=task.timeout_seconds)
        except asyncio.TimeoutError:
            await self.stop_container(container_name)
            return ExecutionResult(
                task_id=task_id,
                exit_code=124,
                stderr=f"Task timed out after {task.timeout_seconds} seconds",
                metadata={
                    "backend": "docker",
                    "image": self.image,
                    "timeout": task.timeout_seconds,
                    "security_profile": security.name,
                },
            )

        return ExecutionResult(
            task_id=task_id,
            exit_code=process.returncode or 0,
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            metadata={
                "backend": "docker",
                "image": self.image,
                "command": task.command,
                "arguments": task.arguments,
                "docker_command": command,
                "security_profile": security.name,
                "container": container_name,
                "security": {
                    "network_mode": security.network_mode,
                    "read_only_rootfs": security.read_only_rootfs,
                    "memory_limit": security.memory_limit,
                    "cpus": security.cpus,
                    "pids_limit": security.pids_limit,
                    "no_new_privileges": security.no_new_privileges,
                },
            },
        )


@dataclass(slots=True)
class DockerExecutionProvider:
    runtime: DockerRuntimeManager

    async def execute(self, task: ExecutionTask) -> ExecutionResult:
        return await self.runtime.run(task)
