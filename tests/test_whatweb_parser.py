from mcaoe.parsers.whatweb import parse_whatweb_output


SAMPLE_WHATWEB_JSON = """
[
  {
    "target": "https://example.com",
    "plugins": {
      "nginx": {"version": "1.24.0"},
      "TLS": {"string": "enabled"}
    }
  }
]
"""


def test_parse_whatweb_output_extracts_technologies_and_evidence() -> None:
    result = parse_whatweb_output(SAMPLE_WHATWEB_JSON)

    assert result.technologies
    assert any(technology.name == "nginx" for technology in result.technologies)
    assert any(technology.name == "TLS" for technology in result.technologies)
    assert result.evidence
    assert result.summary()["technologies"] == 2


def test_parse_whatweb_plaintext_extracts_technologies() -> None:
    result = parse_whatweb_output('[200] [nginx] [TLS] https://example.com')

    assert result.technologies
    assert any(technology.name == "nginx" for technology in result.technologies)
    assert any(technology.name == "TLS" for technology in result.technologies)