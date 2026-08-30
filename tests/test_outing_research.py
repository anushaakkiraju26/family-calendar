import asyncio
import json

import family_activity_agent.agent as agent_module
from family_activity_agent.agent import (
    SAN_JOSE_OFFICIAL_OUTING_DOMAINS,
    coordinated_outing_research_tool,
    official_outing_research_tool,
)


class FakeTool:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def ainvoke(self, arguments):
        self.calls.append(arguments)
        return self.result


def test_san_jose_research_is_restricted_to_official_domains(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(agent_module, "PROJECT_ROOT", tmp_path)
    search = FakeTool(json.dumps({"results": {"web": [
        {
            "url": "https://www.thetech.org/education/camp/",
            "title": "STEM Summer Camp",
        },
        {
            "url": "https://parks.sccgov.org/trails",
            "title": "County Park Hiking Trails",
        },
    ]}}))
    contents = FakeTool(
        "official page content [Trail detail]"
        "(https://parks.sccgov.org/trails/featured-trail)"
    )
    tool = official_outing_research_tool(search, contents)

    result = asyncio.run(tool.ainvoke({
        "query": "San Jose museum park zoo",
        "count": 8,
    }))

    assert search.calls[0]["include_domains"] == SAN_JOSE_OFFICIAL_OUTING_DOMAINS
    assert "exclude_domains" not in search.calls[0]
    assert search.calls[0]["query"] == (
        "San Jose museum park zoo official visitor information"
    )
    assert search.calls[1]["query"] == (
        "San Jose official science museum nature center family visit"
    )
    assert search.calls[2]["query"] == (
        "San Jose official parks hiking trails family visit"
    )
    assert contents.calls[0]["urls"] == ["https://parks.sccgov.org/trails"]
    assert json.loads(result)["status"] == "research_complete"
    evidence = json.loads(
        (tmp_path / "work" / "outing_web_evidence.json").read_text()
    )
    assert evidence["candidate_urls"] == ["https://parks.sccgov.org/trails"]
    assert "https://parks.sccgov.org/trails/featured-trail" in evidence["source_urls"]


def test_san_jose_research_deduplicates_url_variants(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "PROJECT_ROOT", tmp_path)
    search = FakeTool(json.dumps({"results": {"web": [
        {"url": "https://www.sanjoseca.gov/park/123?amp=&utm_source=test"},
        {"url": "https://www.sanjoseca.gov/park/123?amp=&amp="},
    ]}}))
    contents = FakeTool("official page content")
    tool = official_outing_research_tool(search, contents)

    asyncio.run(tool.ainvoke({"query": "San Jose outdoor activities"}))

    assert contents.calls[0]["urls"] == ["https://www.sanjoseca.gov/park/123"]


def test_non_san_jose_research_excludes_aggregators(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "PROJECT_ROOT", tmp_path)
    search = FakeTool(json.dumps({
        "results": {"web": [{"url": "https://example.org/park"}]}
    }))
    contents = FakeTool("official page content")
    tool = official_outing_research_tool(search, contents)

    asyncio.run(tool.ainvoke({"query": "Seattle family outdoor museum"}))

    assert "include_domains" not in search.calls[0]
    assert "tripadvisor.com" in search.calls[0]["exclude_domains"]


def test_coordinated_research_checks_both_calendars_and_web(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(agent_module, "PROJECT_ROOT", tmp_path)
    family_events = FakeTool("[]")
    school_events = FakeTool("[]")
    search = FakeTool(json.dumps({
        "results": {"web": [{"url": "https://www.thetech.org/"}]}
    }))
    contents = FakeTool("official page content")
    tool = coordinated_outing_research_tool(
        family_events, school_events, search, contents
    )

    result = json.loads(asyncio.run(tool.ainvoke({
        "family_id": "family-1",
        "start_date": "2026-08-29",
        "end_date": "2026-08-30",
        "query": "San Jose hiking trails museum",
    })))

    assert result["status"] == "calendar_and_research_complete"
    assert family_events.calls[0]["family_id"] == "family-1"
    assert family_events.calls[0]["start_at"].startswith("2026-08-29T00:00:00")
    assert family_events.calls[0]["end_at"].startswith("2026-08-31T00:00:00")
    assert school_events.calls[0] == {
        "start_date": "2026-08-29",
        "end_date": "2026-08-30",
    }
    assert search.calls
    assert contents.calls
