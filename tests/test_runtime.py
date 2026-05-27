import asyncio

import mcaoe.runtime.docker as docker_module

from mcaoe.runtime.docker import DockerExecutionProvider, DockerRuntimeManager
from mcaoe.execution.provider import ExecutionTask


def test_runtime_status_has_explicit_fields() -> None:
    runtime = DockerRuntimeManager()
    status = runtime.status().as_dict()

    assert status["image"] == "blackarchlinux/blackarch"
    assert status["healthy"] is False
    assert "Docker executable" in status["message"]


def test_runtime_run_returns_graceful_error_when_docker_missing() -> None:
    runtime = DockerRuntimeManager()
    original_which = docker_module.shutil.which
    docker_module.shutil.which = lambda _: None
    try:
        result = asyncio.run(runtime.run(ExecutionTask(command="nmap", arguments=["-V"])))
    finally:
        docker_module.shutil.which = original_which

    assert result.exit_code == 127
    assert "Docker executable" in result.stderr
    assert result.metadata["backend"] == "docker"


def test_runtime_run_builds_docker_command() -> None:
    runtime = DockerRuntimeManager(container_name_prefix="mcaoe-test")
    captured: dict[str, object] = {}

    original_which = docker_module.shutil.which
    original_create = docker_module.asyncio.create_subprocess_exec
    docker_module.shutil.which = lambda _: "/usr/bin/docker"

    class _Process:
        returncode = 0

        async def communicate(self):
            return b"hello", b""

        def kill(self):
            captured["killed"] = True

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _Process()

    docker_module.asyncio.create_subprocess_exec = fake_create_subprocess_exec
    try:
        result = asyncio.run(runtime.run(ExecutionTask(command="echo", arguments=["hello"])))
    finally:
        docker_module.shutil.which = original_which
        docker_module.asyncio.create_subprocess_exec = original_create

    assert result.exit_code == 0
    assert result.stdout == "hello"
    assert captured["args"][0] == "/usr/bin/docker"
    assert captured["args"][1:4] == ("run", "--rm", "--name")
    assert "--network" in captured["args"]
    assert "--memory" in captured["args"]
    assert "--cpus" in captured["args"]
    assert "--pids-limit" in captured["args"]
    assert "--security-opt" in captured["args"]
    assert result.metadata["backend"] == "docker"
    assert result.metadata["command"] == "echo"
    assert result.metadata["security_profile"] == "recon_standard"


def test_runtime_run_uses_defensive_strict_profile_for_dfir_tasks() -> None:
    runtime = DockerRuntimeManager(container_name_prefix="mcaoe-test")
    captured: dict[str, object] = {}

    original_which = docker_module.shutil.which
    original_create = docker_module.asyncio.create_subprocess_exec
    docker_module.shutil.which = lambda _: "/usr/bin/docker"

    class _Process:
        returncode = 0

        async def communicate(self):
            return b"ok", b""

        def kill(self):
            captured["killed"] = True

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        return _Process()

    docker_module.asyncio.create_subprocess_exec = fake_create_subprocess_exec
    try:
        result = asyncio.run(runtime.run(ExecutionTask(command="echo", arguments=["ok"], profile="dfir")))
    finally:
        docker_module.shutil.which = original_which
        docker_module.asyncio.create_subprocess_exec = original_create

    assert result.exit_code == 0
    assert result.metadata["security_profile"] == "defensive_strict"
    assert result.metadata["security"]["network_mode"] == "none"
    assert "--read-only" in captured["args"]


def test_docker_execution_provider_delegates_to_runtime() -> None:
    class FakeRuntime:
        def __init__(self) -> None:
            self.seen: ExecutionTask | None = None

        async def run(self, task: ExecutionTask):
            self.seen = task
            return "delegated"

    runtime = FakeRuntime()
    provider = DockerExecutionProvider(runtime=runtime)  # type: ignore[arg-type]

    result = asyncio.run(provider.execute(ExecutionTask(command="whoami")))

    assert result == "delegated"
    assert runtime.seen is not None
    assert runtime.seen.command == "whoami"
