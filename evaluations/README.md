# Evaluation suite

`cases.json` is the course-facing behavior matrix. It records natural-language
requests, expected MCP tools, approval boundaries, outcomes, and failure paths.

Run the offline automated suite with:

```bash
pytest
```

The tests include real MCP subprocess discovery and invocation, a mutation that
must pause for LangGraph approval before changing SQLite, repository lifecycle
and conflict rules, reminder-draft validation, state isolation, and CLI error
formatting. The deterministic fake chat model avoids Nebius usage while preserving
the actual Deep Agent, LangGraph interrupt, MCP subprocess, and SQLite layers.

Before recording the demo, run selected prompts from `cases.json` with the live
Nebius-backed CLI and record observed tool calls and outcomes in the project
documentation. Live model behavior is intentionally not part of CI.

The family-outing case additionally requires `YDC_API_KEY`. It verifies that
calendar and school checks happen before one `you-search` MCP call, that results
retain source URLs, and that research never creates an event automatically.
