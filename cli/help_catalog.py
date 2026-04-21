"""Plain-English help text catalog."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class HelpEntry:
    """Help text for one operation."""

    short: str
    long: str
    examples: list[str]
    params: dict[str, str]
    warnings: list[str] = field(default_factory=list)


CATALOG: dict[str, HelpEntry] = {
    "healthz_healthz_get": HelpEntry(
        short="Quick check that the server is running.",
        long="Ask the backend if it is alive. This is the fastest command and does not inspect app data.",
        examples=["$ ocean health"],
        params={},
    ),
    "admin_health_api_admin_health_get": HelpEntry(
        short="Show backend status and basic counters.",
        long="See whether the backend is healthy and how many agents, publishers, reviews, and teams are stored.",
        examples=["$ ocean admin health"],
        params={},
    ),
    "list_agents_api_agents_get": HelpEntry(
        short="List every registered agent.",
        long="Show all agent profiles in the system. The default view is a table for quick scanning.",
        examples=["$ ocean agents list", "$ ocean agents list --format json"],
        params={},
    ),
    "create_agent_api_agents_post": HelpEntry(
        short="Register a new agent profile.",
        long="Create a new agent record. You can send full JSON or set top-level fields one by one.",
        examples=[
            '$ ocean agents create --body \'{"name":"Research Bot"}\'',
            '$ ocean agents create --field name="Research Bot" --field description="Summarizes papers"',
        ],
        params={
            "body": "The full JSON object to send.",
            "body-file": "Path to a JSON file with the data to send.",
            "field": "One top-level field in key=value form. Repeat as needed.",
        },
    ),
    "search_agents_api_agents_search_get": HelpEntry(
        short="Find agents by keyword or tag.",
        long="Search agent profiles by text and tags. Results come back in ranked order.",
        examples=[
            "$ ocean agents search --q research",
            "$ ocean agents search --tags research --limit 3",
        ],
        params={
            "q": "Text to match against agent names and descriptions.",
            "tags": "Comma-separated tag filter text from the backend.",
            "weights": "JSON text that adjusts ranking weights.",
            "limit": "How many results to return.",
        },
    ),
    "get_agent_api_agents__agent_id__get": HelpEntry(
        short="Show the full profile of one agent.",
        long="Fetch one agent by its unique ID and print every field the backend returns.",
        examples=["$ ocean agents get <AGENT_ID>"],
        params={"agent-id": 'The agent ID. You can find one with "ocean agents list".'},
    ),
    "update_agent_api_agents__agent_id__patch": HelpEntry(
        short="Change parts of an agent profile.",
        long="Update only the fields you send. Missing fields stay unchanged.",
        examples=[
            '$ ocean agents update <AGENT_ID> --field description="Updated text"',
            "$ ocean agents update <AGENT_ID> --body-file patch.json",
        ],
        params={
            "agent-id": "The agent ID to update.",
            "body": "A JSON object with the fields to change.",
            "body-file": "Path to a JSON file with the fields to change.",
            "field": "One top-level field in key=value form. Repeat as needed.",
        },
    ),
    "get_agent_stats_api_agents__agent_id__stats_get": HelpEntry(
        short="Show how reliable an agent has been.",
        long="See call counts, success rate, timing, and the current health label for one agent.",
        examples=["$ ocean agents stats <AGENT_ID>"],
        params={"agent-id": "The agent ID to inspect."},
    ),
    "get_agent_threads_api_agents__agent_id__threads_get": HelpEntry(
        short="List conversations this agent joined.",
        long="Show thread summaries for one agent so you can trace its recent work.",
        examples=["$ ocean agents threads <AGENT_ID>"],
        params={"agent-id": "The agent ID to inspect."},
    ),
    "list_publishers_api_publishers_get": HelpEntry(
        short="List every publisher and verification state.",
        long="Show all publishers with their names, titles, and whether they are verified.",
        examples=["$ ocean publishers list"],
        params={},
    ),
    "create_publisher_api_publishers_post": HelpEntry(
        short="Register a new publisher.",
        long="Create a publisher record. New publishers start unverified.",
        examples=[
            '$ ocean publishers create --field name="Jane Doe" --field title="Researcher"'
        ],
        params={
            "body": "The full JSON object to send.",
            "body-file": "Path to a JSON file with the data to send.",
            "field": "One top-level field in key=value form. Repeat as needed.",
        },
    ),
    "get_publisher_api_publishers__publisher_id__get": HelpEntry(
        short="Show one publisher profile.",
        long="Fetch a publisher by ID and show the current verification details.",
        examples=["$ ocean publishers get <PUBLISHER_ID>"],
        params={
            "publisher-id": 'The publisher ID. Find one with "ocean publishers list".'
        },
    ),
    "verify_publisher_api_publishers__publisher_id__verify_post": HelpEntry(
        short="Grant the verified badge to a publisher.",
        long="Mark one publisher as verified. You can attach a short note that explains the evidence.",
        examples=[
            '$ ocean publishers verify <PUBLISHER_ID> --field note="Checked manually"'
        ],
        params={
            "publisher-id": "The publisher ID to verify.",
            "body": "The full JSON object to send.",
            "body-file": "Path to a JSON file with the data to send.",
            "field": "One top-level field in key=value form. Repeat as needed.",
        },
    ),
    "unverify_publisher_api_publishers__publisher_id__unverify_post": HelpEntry(
        short="Remove a publisher verification badge.",
        long="Mark one publisher as unverified and clear its saved verification note.",
        examples=["$ ocean publishers unverify <PUBLISHER_ID>"],
        params={"publisher-id": "The publisher ID to unverify."},
    ),
    "get_thread_api_threads__thread_id__get": HelpEntry(
        short="Show one conversation thread and its messages.",
        long="Fetch a thread by ID and include the messages that belong to it.",
        examples=["$ ocean threads get <THREAD_ID>"],
        params={"thread-id": "The thread ID to inspect."},
    ),
    "list_teams_api_teams_get": HelpEntry(
        short="List every team that has been assembled.",
        long="Show the teams currently stored in the backend.",
        examples=["$ ocean teams list"],
        params={},
    ),
    "delete_team_api_teams__team_id__delete": HelpEntry(
        short="Delete one team.",
        long="Delete a team by ID. This removes it from the backend.",
        examples=["$ ocean teams delete <TEAM_ID> --yes"],
        params={
            "team-id": "The team ID to delete.",
            "yes": "Skip the confirmation prompt.",
        },
        warnings=["This cannot be undone."],
    ),
    "upload_orchestrator_api_orchestrator_upload_post": HelpEntry(
        short="Upload a Python orchestrator file.",
        long="Send a Python template file to the backend so it can create a demo session.",
        examples=[
            "$ ocean orchestrator upload --body-file agents/orchestrator_template.py"
        ],
        params={"body-file": "Path to the Python file to upload."},
    ),
    "download_template_api_orchestrator_template_get": HelpEntry(
        short="Download the orchestrator template.",
        long="Fetch the starter Python template you can edit and upload later.",
        examples=["$ ocean orchestrator template --format raw"],
        params={},
    ),
    "github_webhook_api_github_webhook_post": HelpEntry(
        short="Send a test GitHub event to the backend.",
        long="Post a sample GitHub event payload with the matching event header so you can test the webhook flow locally.",
        examples=[
            "$ ocean github webhook --x-github-event release --body-file release.json"
        ],
        params={
            "x-github-event": "The GitHub event name, such as release or star.",
            "body": "The full JSON object to send.",
            "body-file": "Path to a JSON file with the event data.",
        },
    ),
    "demo_stream_api_demo_stream_get": HelpEntry(
        short="Watch the orchestrator demo live.",
        long="Open a live stream of events from the demo. You can stop with Ctrl+C at any time.",
        examples=[
            "$ ocean demo stream --max-events 3",
            "$ ocean demo stream --session-id <SESSION_ID>",
        ],
        params={
            "session-id": "A session ID returned by the upload command.",
            "max-events": "Stop after this many events.",
            "timeout": "Stop after this many seconds.",
            "raw": "Print the raw stream instead of formatted events.",
        },
    ),
}
