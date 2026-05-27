from mcaoe.parsers.nmap_xml import parse_nmap_xml


SAMPLE_NMAP_XML = """
<nmaprun>
  <host>
    <status state="up" />
    <address addr="192.0.2.10" />
    <hostnames>
      <hostname name="example.local" />
    </hostnames>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open" />
        <service name="http" product="nginx" version="1.24" />
      </port>
    </ports>
  </host>
  <host>
    <status state="down" />
    <address addr="192.0.2.11" />
  </host>
</nmaprun>
"""


def test_parse_nmap_xml_extracts_host_and_service() -> None:
    result = parse_nmap_xml(SAMPLE_NMAP_XML)

    assert len(result.hosts) == 1
    assert result.hosts[0].address == "192.0.2.10"
    assert result.hosts[0].hostname == "example.local"
    assert len(result.services) == 1
    assert result.services[0].name == "http"
    assert result.services[0].port == 80
    assert result.services[0].version == "1.24"
    assert len(result.evidence) >= 3
    assert result.technologies
    assert any(technology.name == "web service" for technology in result.technologies)
def test_parse_nmap_xml_summarizes_counts() -> None:
    result = parse_nmap_xml(SAMPLE_NMAP_XML)

    summary = result.summary()

    assert summary["hosts"] == 1
    assert summary["services"] == 1
    assert summary["technologies"] >= 1
