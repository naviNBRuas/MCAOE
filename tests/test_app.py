from mcaoe.app import build_parser


def test_build_parser_returns_argument_parser() -> None:
    parser = build_parser()
    assert parser.prog == "mcaoe"


def test_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.session_name == "default"
    assert args.database == ".mcaoe/mcaoe.sqlite3"
    assert args.log_level == "INFO"
    assert args.capability == "web_security"
    assert args.no_ui is False
    assert args.dry_run is False
    assert args.runtime == "local"
    assert args.report_format == "markdown"


def test_parser_supports_session_management() -> None:
    parser = build_parser()
    args = parser.parse_args(["--list-sessions"])
    assert args.list_sessions is True

    args = parser.parse_args(["--session-count"])
    assert args.session_count is True

    args = parser.parse_args(["--delete-session", "abc-123"])
    assert args.delete_session == "abc-123"

    args = parser.parse_args(["--load-session", "abc-123"])
    assert args.load_session == "abc-123"


def test_parser_knows_all_capabilities() -> None:
    parser = build_parser()
    args = parser.parse_args(["--capability", "ctf"])
    assert args.capability == "ctf"

    args = parser.parse_args(["--capability", "infrastructure"])
    assert args.capability == "infrastructure"


def test_parser_supports_export_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["--export-report", "/tmp/report.md", "--report-format", "json"])
    assert args.export_report == "/tmp/report.md"
    assert args.report_format == "json"


def test_parser_supports_list_plugins() -> None:
    parser = build_parser()
    args = parser.parse_args(["--list-plugins"])
    assert args.list_plugins is True


def test_parser_supports_list_profiles() -> None:
    parser = build_parser()
    args = parser.parse_args(["--list-profiles"])
    assert args.list_profiles is True


def test_parser_supports_dry_run() -> None:
    parser = build_parser()
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True


def test_parser_supports_runtime_selection() -> None:
    parser = build_parser()
    args = parser.parse_args(["--runtime", "docker"])
    assert args.runtime == "docker"


def test_parser_supports_headless_mode() -> None:
    parser = build_parser()
    args = parser.parse_args(["--no-ui", "--target", "example.com", "--plugin", "nmap"])
    assert args.no_ui is True
    assert args.target == "example.com"
    assert args.plugin == "nmap"
