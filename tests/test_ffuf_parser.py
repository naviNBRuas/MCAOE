from mcaoe.parsers.ffuf import parse_ffuf_output


SAMPLE_FFUF_JSON = """
{
  "results": [
    {
      "url": "https://example.com/admin/",
      "status": 403,
      "length": 1234,
      "words": 120,
      "lines": 32,
      "redirectlocation": ""
    },
    {
      "url": "https://example.com/healthz",
      "status": 200,
      "length": 42,
      "words": 4,
      "lines": 1
    }
  ]
}
"""


def test_parse_ffuf_output_extracts_results_findings_and_unknowns() -> None:
    result = parse_ffuf_output(SAMPLE_FFUF_JSON)

    assert result.results
    assert any(item.url.endswith("/admin/") for item in result.results)
    assert any(finding.title == "Interesting content discovered" for finding in result.findings)
    assert any(finding.title == "Restricted content discovered" for finding in result.findings)
    assert result.evidence
    assert result.summary()["results"] == 2


def test_parse_ffuf_plaintext_extracts_results_and_classifies_statuses() -> None:
    result = parse_ffuf_output('/admin/ [403] [1234 words] [32 lines]\n/healthz [200] [42 words] [1 lines]\n')

    assert result.results
    assert any(item.status == 403 for item in result.results)
    assert any(item.status == 200 for item in result.results)
    assert any(finding.title == "Restricted content discovered" for finding in result.findings)
    assert any(finding.title == "Interesting content discovered" for finding in result.findings)