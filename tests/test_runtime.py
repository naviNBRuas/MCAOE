import asyncio
from unittest.mock import patch

from mcaoe.runtime.docker import DockerExecutionProvider, DockerRuntimeManager
from mcaoe.execution.provider import ExecutionTask


def test_runtime_status_has_explicit_fields() -> None:
    with patch("mcaoe.runtime.docker.shutil.which", return_value=None):
        runtime = DockerRuntimeManager()
        status = runtime.status().as_dict()

    assert status["image"] == "blackarchlinux/blackarch"
    assert status["healthy"] is False
    assert "Docker executable" in str(status["message"])


def test_runtime_run_returns_graceful_error_when_docker_missing() -> None:
    with patch("mcaoe.runtime.docker.shutil.which", return_value=None):
        runtime = DockerRuntimeManager()
        result = asyncio.run(runtime.run(ExecutionTask(command="nmap", arguments=["-V"])))

    assert result.exit_code == 127
    assert "Docker executable" in result.stderr
    assert result.metadata["backend"] == "docker"


def test_runtime_run_builds_docker_command() -> None:
    captured: dict[str, object] = {}

    class _Process:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"hello", b""

        def kill(self) -> None:
            captured["killed"] = True

    async def fake_create_subprocess_exec(*args: object, **kwargs: object) -> _Process:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _Process()

    with (
        patch("mcaoe.runtime.docker.shutil.which", return_value="/usr/bin/docker"),
        patch("mcaoe.runtime.docker.asyncio.create_subprocess_exec", new=fake_create_subprocess_exec),
    ):
        runtime = DockerRuntimeManager(container_name_prefix="mcaoe-test")
        result = asyncio.run(runtime.run(ExecutionTask(command="echo", arguments=["hello"])))

    assert result.exit_code == 0
    assert result.stdout == "hello"
    args = captured.get("args", ())
    assert isinstance(args, tuple) and args[0] == "/usr/bin/docker"
    assert isinstance(args, tuple) and args[1:4] == ("run", "--rm", "--name")
    assert "--network" in str(captured.get("args", ""))
    assert "--memory" in str(captured.get("args", ""))
    assert "--cpus" in str(captured.get("args", ""))
    assert "--pids-limit" in str(captured.get("args", ""))
    assert "--security-opt" in str(captured.get("args", ""))
    assert result.metadata["backend"] == "docker"
    assert result.metadata["command"] == "echo"
    assert result.metadata["security_profile"] == "recon_standard"


def test_runtime_run_uses_defensive_strict_profile_for_dfir_tasks() -> None:
    captured: dict[str, object] = {}

    class _Process:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"ok", b""

        def kill(self) -> None:
            captured["killed"] = True

    async def fake_create_subprocess_exec(*args: object, **kwargs: object) -> _Process:
        captured["args"] = args
        return _Process()

    with (
        patch("mcaoe.runtime.docker.shutil.which", return_value="/usr/bin/docker"),
        patch("mcaoe.runtime.docker.asyncio.create_subprocess_exec", new=fake_create_subprocess_exec),
    ):
        runtime = DockerRuntimeManager(container_name_prefix="mcaoe-test")
        result = asyncio.run(runtime.run(ExecutionTask(command="echo", arguments=["ok"], profile="dfir")))

    assert result.exit_code == 0
    assert result.metadata["security_profile"] == "defensive_strict"
    assert result.metadata["security"]["network_mode"] == "none"
    assert "--read-only" in str(captured.get("args", ""))


def test_runtime_run_returns_container_name_in_metadata() -> None:
    captured: dict[str, object] = {}

    class _Process:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"out", b""

    async def fake_create_subprocess_exec(*args: object, **kwargs: object) -> _Process:
        captured["args"] = args
        return _Process()

    with (
        patch("mcaoe.runtime.docker.shutil.which", return_value="/usr/bin/docker"),
        patch("mcaoe.runtime.docker.asyncio.create_subprocess_exec", new=fake_create_subprocess_exec),
    ):
        runtime = DockerRuntimeManager()
        result = asyncio.run(runtime.run(ExecutionTask(command="echo", arguments=["hi"])))

    assert "container" in result.metadata
    assert result.metadata["container"].startswith("mcaoe-")


def test_stream_logs_returns_graceful_error_when_docker_missing() -> None:
    with patch("mcaoe.runtime.docker.shutil.which", return_value=None):
        runtime = DockerRuntimeManager()
        result = asyncio.run(runtime.stream_logs(ExecutionTask(command="echo", arguments=["hello"])))

    assert result.exit_code == 127
    assert "Docker executable" in result.stderr


def test_stream_logs_invokes_docker_run() -> None:
    captured: dict[str, object] = {}

    class _StreamReader:
        async def readline(self) -> bytes:
            return b""

    class _Process:
        returncode = 0
        stdout = _StreamReader()
        stderr = _StreamReader()

        async def wait(self) -> int:
            return 0

    async def fake_create_subprocess_exec(*args: object, **kwargs: object) -> _Process:
        captured["args"] = args
        return _Process()

    with (
        patch("mcaoe.runtime.docker.shutil.which", return_value="/usr/bin/docker"),
        patch("mcaoe.runtime.docker.asyncio.create_subprocess_exec", new=fake_create_subprocess_exec),
    ):
        runtime = DockerRuntimeManager(container_name_prefix="mcaoe-stream")
        result = asyncio.run(runtime.stream_logs(ExecutionTask(command="echo", arguments=["stream"])))

    assert result.exit_code == 0
    args = captured.get("args", ())
    assert isinstance(args, tuple) and args[1:4] == ("run", "--rm", "--name")
    assert "stream" in str(captured.get("args", ""))


def test_runtime_stop_container_noop_when_docker_missing() -> None:
    with patch("mcaoe.runtime.docker.shutil.which", return_value=None):
        runtime = DockerRuntimeManager()
        asyncio.run(runtime.stop_container("test-container"))


def test_runtime_cleanup_flag_default_true() -> None:
    runtime = DockerRuntimeManager()
    assert runtime.container_cleanup is True


def test_docker_execution_provider_delegates_to_runtime() -> None:
    from mcaoe.execution.provider import ExecutionResult

    class FakeRuntime:
        def __init__(self) -> None:
            self.seen: ExecutionTask | None = None

        async def run(self, task: ExecutionTask) -> ExecutionResult:
            self.seen = task
            from uuid import uuid4
            return ExecutionResult(task_id=uuid4(), exit_code=0, stdout="delegated")

    fake_runtime = FakeRuntime()
    provider = DockerExecutionProvider(runtime=fake_runtime)  # type: ignore[arg-type]

    result = asyncio.run(provider.execute(ExecutionTask(command="whoami")))

    assert result.stdout == "delegated"
    assert fake_runtime.seen is not None
    assert fake_runtime.seen.command == "whoami"
