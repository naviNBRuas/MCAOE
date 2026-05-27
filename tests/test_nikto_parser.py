from mcaoe.parsers.nikto import parse_nikto_output


SAMPLE_NIKTO_OUTPUT = """
+ Target IP: 192.0.2.10
+ Target Hostname: example.local
+ Server: nginx/1.24.0
+ /: X-Frame-Options header not present.
+ /admin/: Directory indexing found.
"""


def test_parse_nikto_output_extracts_findings_and_technology() -> None:
    result = parse_nikto_output(SAMPLE_NIKTO_OUTPUT)

    assert result.technologies
    assert any(technology.name == "nginx" for technology in result.technologies)
    assert len(result.findings) >= 2
    assert any(finding.title == "Missing X-Frame-Options header" for finding in result.findings)
    assert any(finding.title == "Directory indexing enabled" for finding in result.findings)
    assert result.evidence
    assert result.summary()["findings"] >= 2