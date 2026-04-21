"""E2E tests for the ocean CLI against a live backend.

Covers TEST_CASE_CLI.md: TC-01-xx, TC-02-xx, TC-03-xx, TC-05-xx,
TC-07-xx, TC-08-xx, TC-13-01~20, S1~S7.

Excluded (automation limits):
- TC-13-21 demo stream (SSE blocks CliRunner)
- TC-05-01 Rich TTY (CliRunner has no TTY)
- TC-06-xx SSE renderer (blocking)
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from cli.errors import HttpClientError, NetworkError


def _invoke(app, runner, args: list[str], *, catch_exceptions: bool = False):
    """Invoke CLI app and return result."""
    return runner.invoke(app, args, catch_exceptions=catch_exceptions)


# ──────────────────────────────────────────────────────────────────────────────
# F-01: Spec Loading — TC-01-xx
# ──────────────────────────────────────────────────────────────────────────────
class TestSpecLoading:
    def test_tc01_04_offline_no_cache_exits4(self) -> None:
        """TC-01-04: --offline without cache → SpecUnavailable raised."""
        import tempfile

        import httpx

        from cli.config import load_settings
        from cli.errors import SpecUnavailable
        from cli.spec_loader import SpecLoader

        with tempfile.TemporaryDirectory() as td:
            settings = load_settings(
                {
                    "offline": True,
                    "cache_dir": str(Path(td) / "empty"),
                    "base_url": "http://127.0.0.1:19999",
                }
            )
            http = httpx.Client()
            try:
                with pytest.raises(SpecUnavailable):
                    SpecLoader(settings, http).load()
            finally:
                http.close()

    def test_tc01_05_spec_override_loads(self, make_cli, live_server: str) -> None:
        """TC-01-05: --spec docs/openapi.json (override) → help works."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["--help"])
        assert result.exit_code == 0
        assert "agents" in result.output


# ──────────────────────────────────────────────────────────────────────────────
# F-02: Dynamic Command Binding — TC-02-xx
# ──────────────────────────────────────────────────────────────────────────────
class TestCommandBinding:
    _EXPECTED_GROUPS = [
        "agents",
        "publishers",
        "threads",
        "teams",
        "orchestrator",
        "github",
        "demo",
        "admin",
    ]
    _EXPECTED_AGENT_CMDS = [
        "list",
        "create",
        "get",
        "update",
        "search",
        "stats",
        "threads",
    ]
    _ALL_OPERATIONS: list[list[str]] = [
        ["health", "--help"],
        ["admin", "health", "--help"],
        ["agents", "list", "--help"],
        ["agents", "create", "--help"],
        ["agents", "get", "--help"],
        ["agents", "update", "--help"],
        ["agents", "search", "--help"],
        ["agents", "stats", "--help"],
        ["agents", "threads", "--help"],
        ["publishers", "list", "--help"],
        ["publishers", "create", "--help"],
        ["publishers", "get", "--help"],
        ["publishers", "verify", "--help"],
        ["publishers", "unverify", "--help"],
        ["threads", "get", "--help"],
        ["teams", "list", "--help"],
        ["teams", "delete", "--help"],
        ["orchestrator", "upload", "--help"],
        ["orchestrator", "template", "--help"],
        ["github", "webhook", "--help"],
        ["demo", "stream", "--help"],
    ]

    def test_tc02_01_all_8_groups_visible(self, make_cli, live_server: str) -> None:
        """TC-02-01: ocean --help exposes all 8 command groups."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["--help"])
        assert result.exit_code == 0
        for group in self._EXPECTED_GROUPS:
            assert group in result.output, f"Group '{group}' missing from --help"

    def test_tc02_02_agents_group_commands(self, make_cli, live_server: str) -> None:
        """TC-02-02: ocean agents --help shows 7 expected sub-commands."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["agents", "--help"])
        assert result.exit_code == 0
        for cmd in self._EXPECTED_AGENT_CMDS:
            assert cmd in result.output, f"Command '{cmd}' missing from agents --help"

    @pytest.mark.parametrize("args", _ALL_OPERATIONS)
    def test_tc02_03_all_21_operations_help(
        self, make_cli, live_server: str, args: list[str]
    ) -> None:
        """TC-02-03: All 21 operations respond to --help with exit 0."""
        app, runner = make_cli(live_server)
        result = runner.invoke(app, args)
        assert result.exit_code == 0, (
            f"--help failed for {args!r}: exit={result.exit_code}\n{result.output}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# F-03: Parameter Binding — TC-03-xx
# ──────────────────────────────────────────────────────────────────────────────
class TestParameterBinding:
    def test_tc03_01_path_param_required(self, make_cli, live_server: str) -> None:
        """TC-03-01: ocean agents get (no arg) → non-zero exit."""
        app, runner = make_cli(live_server)
        result = runner.invoke(app, ["agents", "get"])
        assert result.exit_code != 0

    def test_tc03_02_path_param_normal(
        self, make_cli, live_server: str, seed_ids: dict
    ) -> None:
        """TC-03-02: ocean agents get <ID> --format json returns agent profile."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            ["agents", "get", seed_ids["research"], "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == seed_ids["research"]
        assert "name" in data

    def test_tc03_06_body_post(self, make_cli, live_server: str) -> None:
        """TC-03-06: ocean agents create --body '...' → 201 with id field."""
        app, runner = make_cli(live_server)
        body = json.dumps({"name": "TC-03-06 Agent", "description": "body post"})
        result = _invoke(
            app,
            runner,
            ["agents", "create", "--body", body, "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "id" in data
        assert data["name"] == "TC-03-06 Agent"

    def test_tc03_08_field_shortcut(self, make_cli, live_server: str) -> None:
        """TC-03-08: ocean agents create --field key=value builds body correctly."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            [
                "agents",
                "create",
                "--field",
                "name=TC-03-08 Agent",
                "--field",
                "description=field test",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "TC-03-08 Agent"


# ──────────────────────────────────────────────────────────────────────────────
# F-05: Output Formats — TC-05-xx
# ──────────────────────────────────────────────────────────────────────────────
class TestOutputFormats:
    def test_tc05_03_format_json(self, make_cli, live_server: str) -> None:
        """TC-05-03: --format json → parse-able JSON array."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["agents", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_tc05_04_format_yaml(self, make_cli, live_server: str) -> None:
        """TC-05-04: --format yaml → parse-able YAML list."""
        import yaml  # PyYAML

        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["agents", "list", "--format", "yaml"])
        assert result.exit_code == 0
        data = yaml.safe_load(result.output)
        assert isinstance(data, list)

    def test_tc05_08_empty_list_returns_array(self, make_cli, live_server: str) -> None:
        """TC-05-08: teams list (likely empty) → JSON array, not error."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["teams", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)


# ──────────────────────────────────────────────────────────────────────────────
# F-07: Error Handling — TC-07-xx
# ──────────────────────────────────────────────────────────────────────────────
class TestErrorHandling:
    def test_tc07_01_404_raises_client_error(self, make_cli, live_server: str) -> None:
        """TC-07-01: Non-existent agent_id → HttpClientError (4xx)."""
        app, runner = make_cli(live_server)
        fake_id = str(uuid.uuid4())
        result = runner.invoke(app, ["agents", "get", fake_id])
        assert isinstance(result.exception, HttpClientError), (
            f"Expected HttpClientError, got {type(result.exception)}: {result.exception}"
        )

    def test_tc07_02_422_missing_name(self, make_cli, live_server: str) -> None:
        """TC-07-02: POST /api/agents with empty body → 422 HttpClientError."""
        app, runner = make_cli(live_server)
        result = runner.invoke(app, ["agents", "create", "--body", "{}"])
        assert isinstance(result.exception, HttpClientError), (
            f"Expected HttpClientError (422), got {type(result.exception)}"
        )

    def test_tc07_04_connection_refused_raises_network_error(self, make_cli) -> None:
        """TC-07-04: No server on port 19999 → NetworkError."""
        app, runner = make_cli("http://127.0.0.1:19999")
        result = runner.invoke(app, ["agents", "list"])
        assert isinstance(result.exception, NetworkError), (
            f"Expected NetworkError, got {type(result.exception)}: {result.exception}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# F-08: Meta Commands — TC-08-xx
# ──────────────────────────────────────────────────────────────────────────────
class TestMetaCommands:
    def test_tc08_01_describe(self, make_cli, live_server: str) -> None:
        """TC-08-01: ocean describe agents create → method and path shown."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["describe", "agents", "create"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "post" in output_lower or "/api/agents" in result.output

    def test_tc08_02_raw_get(self, make_cli, live_server: str) -> None:
        """TC-08-02: ocean raw GET /healthz → {"status":"ok"}."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["raw", "GET", "/healthz"])
        assert result.exit_code == 0
        assert "ok" in result.output

    def test_tc08_04_spec_show(self, make_cli, live_server: str) -> None:
        """TC-08-04: ocean spec show → source and operation count."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["spec", "show"])
        assert result.exit_code == 0
        assert "operations" in result.output or "paths" in result.output


# ──────────────────────────────────────────────────────────────────────────────
# Per-Endpoint Coverage — TC-13-01 ~ TC-13-20
# ──────────────────────────────────────────────────────────────────────────────
class TestEndpointCoverage:
    """21개 operation 1:1 검증. 각 테스트는 독립적이며 DB 상태에 의존하지 않는다."""

    def test_tc13_01_health(self, make_cli, live_server: str) -> None:
        """TC-13-01: GET /healthz → {"status":"ok"}."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["health", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["status"] == "ok"

    def test_tc13_02_admin_health(self, make_cli, live_server: str) -> None:
        """TC-13-02: GET /api/admin/health → includes status field."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["admin", "health", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "status" in data

    def test_tc13_03_agents_list(
        self, make_cli, live_server: str, seed_ids: dict
    ) -> None:
        """TC-13-03: GET /api/agents → JSON array with seed agents (≥5)."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["agents", "list", "--format", "json"])
        assert result.exit_code == 0
        agents = json.loads(result.output)
        assert isinstance(agents, list)
        assert len(agents) >= 5

    def test_tc13_04_agents_create(self, make_cli, live_server: str) -> None:
        """TC-13-04: POST /api/agents → 201 with id and name."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            ["agents", "create", "--field", "name=TC-13-04 Agent", "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "id" in data
        assert data["name"] == "TC-13-04 Agent"

    def test_tc13_05_agents_search(self, make_cli, live_server: str) -> None:
        """TC-13-05: GET /api/agents/search?q=research&limit=3 → ≤3 results."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            ["agents", "search", "--q", "research", "--limit", "3", "--format", "json"],
        )
        assert result.exit_code == 0
        results = json.loads(result.output)
        assert isinstance(results, list)
        assert len(results) <= 3

    def test_tc13_06_agents_get(
        self, make_cli, live_server: str, seed_ids: dict
    ) -> None:
        """TC-13-06: GET /api/agents/{id} → full profile."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            ["agents", "get", seed_ids["research"], "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == seed_ids["research"]
        assert "trust_score" in data

    def test_tc13_07_agents_update(
        self, make_cli, live_server: str, seed_ids: dict
    ) -> None:
        """TC-13-07: PATCH /api/agents/{id} → description updated."""
        app, runner = make_cli(live_server)
        new_desc = f"E2E updated {uuid.uuid4().hex[:6]}"
        result = _invoke(
            app,
            runner,
            [
                "agents",
                "update",
                seed_ids["code"],
                "--field",
                f"description={new_desc}",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["description"] == new_desc

    def test_tc13_08_agents_stats(
        self, make_cli, live_server: str, seed_ids: dict
    ) -> None:
        """TC-13-08: GET /api/agents/{id}/stats → metric fields present."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            ["agents", "stats", seed_ids["research"], "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "success_rate" in data
        assert "avg_response_ms" in data
        # API returns total_invocations (not total_calls)
        assert "total_invocations" in data or "total_calls" in data

    def test_tc13_09_agents_threads(
        self, make_cli, live_server: str, seed_ids: dict
    ) -> None:
        """TC-13-09: GET /api/agents/{id}/threads → JSON array (may be empty)."""
        app, runner = make_cli(live_server)
        result = _invoke(
            app,
            runner,
            ["agents", "threads", seed_ids["pm"], "--format", "json"],
        )
        assert result.exit_code == 0
        assert isinstance(json.loads(result.output), list)

    def test_tc13_10_publishers_list(self, make_cli, live_server: str) -> None:
        """TC-13-10: GET /api/publishers → JSON array with verified field."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["publishers", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 5
        assert "verified" in data[0]

    def test_tc13_11_publishers_create(self, make_cli, live_server: str) -> None:
        """TC-13-11: POST /api/publishers → 201 with verified=false."""
        app, runner = make_cli(live_server)
        unique_name = f"TC Publisher {uuid.uuid4().hex[:8]}"
        result = _invoke(
            app,
            runner,
            [
                "publishers",
                "create",
                "--field",
                f"name={unique_name}",
                "--field",
                "title=E2E Tester",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get("verified") is False

    def test_tc13_12_publishers_get(self, make_cli, live_server: str) -> None:
        """TC-13-12: GET /api/publishers/{id} → publisher profile."""
        app, runner = make_cli(live_server)
        unique_name = f"TC Get {uuid.uuid4().hex[:8]}"
        r_create = _invoke(
            app,
            runner,
            [
                "publishers",
                "create",
                "--field",
                f"name={unique_name}",
                "--field",
                "title=Tester",
                "--format",
                "json",
            ],
        )
        pub_id = json.loads(r_create.output)["id"]

        result = _invoke(app, runner, ["publishers", "get", pub_id, "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["id"] == pub_id

    def test_tc13_13_publishers_verify(self, make_cli, live_server: str) -> None:
        """TC-13-13: POST /api/publishers/{id}/verify → verified=true."""
        app, runner = make_cli(live_server)
        unique_name = f"TC Verify {uuid.uuid4().hex[:8]}"
        r_create = _invoke(
            app,
            runner,
            [
                "publishers",
                "create",
                "--field",
                f"name={unique_name}",
                "--field",
                "title=Tester",
                "--format",
                "json",
            ],
        )
        pub_id = json.loads(r_create.output)["id"]

        result = _invoke(
            app,
            runner,
            [
                "publishers",
                "verify",
                pub_id,
                "--field",
                "note=Confirmed via E2E",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert json.loads(result.output).get("verified") is True

    def test_tc13_14_publishers_unverify(self, make_cli, live_server: str) -> None:
        """TC-13-14: POST /api/publishers/{id}/unverify → verified=false."""
        app, runner = make_cli(live_server)
        unique_name = f"TC Unverify {uuid.uuid4().hex[:8]}"
        r_create = _invoke(
            app,
            runner,
            [
                "publishers",
                "create",
                "--field",
                f"name={unique_name}",
                "--field",
                "title=Tester",
                "--format",
                "json",
            ],
        )
        pub_id = json.loads(r_create.output)["id"]
        _invoke(app, runner, ["publishers", "verify", pub_id, "--format", "json"])

        result = _invoke(
            app, runner, ["publishers", "unverify", pub_id, "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output).get("verified") is False

    def test_tc13_15_threads_get_404(self, make_cli, live_server: str) -> None:
        """TC-13-15: GET /api/threads/{non-existent} → 404 HttpClientError."""
        app, runner = make_cli(live_server)
        fake_id = str(uuid.uuid4())
        result = runner.invoke(app, ["threads", "get", fake_id])
        assert isinstance(result.exception, HttpClientError)

    def test_tc13_16_teams_list(self, make_cli, live_server: str) -> None:
        """TC-13-16: GET /api/teams → JSON array."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["teams", "list", "--format", "json"])
        assert result.exit_code == 0
        assert isinstance(json.loads(result.output), list)

    def test_tc13_18_orchestrator_upload(self, make_cli, live_server: str) -> None:
        """TC-13-18: POST /api/orchestrator/upload → session_id returned."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            plan_file = Path(td) / "plan.py"
            plan_file.write_text(
                'TASK_DESCRIPTION = "Build AI startup team"\n'
                'TEAM_REQUIREMENTS = [{"role": "researcher"}, {"role": "developer"}]\n'
                'AGENT_NAME = "TestOrchestrator"\n'
                'GROQ_MODEL = "llama3-8b-8192"\n',
                encoding="utf-8",
            )
            app, runner = make_cli(live_server)
            result = _invoke(
                app,
                runner,
                [
                    "orchestrator",
                    "upload",
                    "--body-file",
                    str(plan_file),
                    "--format",
                    "json",
                ],
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "session_id" in data
        assert "task_description" in data

    def test_tc13_19_orchestrator_template(self, make_cli, live_server: str) -> None:
        """TC-13-19: GET /api/orchestrator/template → non-empty Python source."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["orchestrator", "template", "--format", "raw"])
        assert result.exit_code == 0
        assert len(result.output.strip()) > 0

    def test_tc13_20_github_webhook(self, make_cli, live_server: str) -> None:
        """TC-13-20: POST /api/github/webhook → ignored (no matching agent).

        The OpenAPI spec has no requestBody for this endpoint, so the binder
        does not add --body. We use the `raw` meta-command to send the payload.
        Without X-GitHub-Event header the endpoint returns {"status":"ignored"}.
        """
        app, runner = make_cli(live_server)
        payload = {
            "repository": {"full_name": "test-user/no-match-repo"},
            "release": {
                "tag_name": "v1.0.0",
                "name": "Test Release",
                "body": "E2E test",
                "published_at": "2026-01-01T00:00:00Z",
            },
        }
        result = _invoke(
            app,
            runner,
            ["raw", "POST", "/api/github/webhook", "--body", json.dumps(payload)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get("status") in ("ok", "ignored")


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Suite — S1 ~ S7
# ──────────────────────────────────────────────────────────────────────────────
class TestSmokeScenarios:
    """CI 최소 스위트. 모두 통과해야 릴리스 가능."""

    def test_s1_admin_health(self, make_cli, live_server: str) -> None:
        """S1: ocean admin health → status field present."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["admin", "health", "--format", "json"])
        assert result.exit_code == 0
        assert "status" in json.loads(result.output)

    def test_s2_agents_list_json(self, make_cli, live_server: str) -> None:
        """S2: ocean agents list --format json → parse-able JSON array."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["agents", "list", "--format", "json"])
        assert result.exit_code == 0
        assert isinstance(json.loads(result.output), list)

    def test_s3_s4_create_then_get(self, make_cli, live_server: str) -> None:
        """S3+S4: create agent → GET same agent by returned id."""
        app, runner = make_cli(live_server)
        r_create = _invoke(
            app,
            runner,
            ["agents", "create", "--field", "name=Smoke-S3 Agent", "--format", "json"],
        )
        assert r_create.exit_code == 0
        agent_id = json.loads(r_create.output)["id"]

        r_get = _invoke(app, runner, ["agents", "get", agent_id, "--format", "json"])
        assert r_get.exit_code == 0
        assert json.loads(r_get.output)["id"] == agent_id

    def test_s5_dry_run_outputs_curl(self, make_cli, live_server: str) -> None:
        """S5: --dry-run → curl command in stdout, no actual network call."""
        from click.testing import CliRunner

        from cli.app import create_click_app
        from cli.client import ApiClient
        from cli.config import load_settings
        from cli.spec_loader import LoadedSpec, SpecSource

        spec_path = Path("docs/openapi.json")
        spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
        settings = load_settings(
            {"base_url": live_server, "spec_override": str(spec_path), "dry_run": True}
        )
        loaded_spec = LoadedSpec(
            spec=spec_data,
            source=SpecSource(
                kind="override", location=str(spec_path), fetched_at=None
            ),
        )
        client = ApiClient(settings)
        try:
            app = create_click_app(settings, loaded_spec, client)
            result = CliRunner().invoke(
                app,
                ["agents", "create", "--field", "name=S5 Agent", "--format", "json"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            assert "curl" in result.output.lower()
        finally:
            client.close()

    def test_s7_describe_agents_list(self, make_cli, live_server: str) -> None:
        """S7: ocean describe agents list → method/path output."""
        app, runner = make_cli(live_server)
        result = _invoke(app, runner, ["describe", "agents", "list"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "get" in output_lower or "/api/agents" in result.output
