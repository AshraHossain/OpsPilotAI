"""
Mock tool implementations for local development.
Returns realistic hardcoded responses so agents can run without any real API credentials.
These are automatically used when APP_ENV=development (the default).

Each function mirrors the signature and @tool decorator of its real counterpart
so CrewAI registers and calls them identically.
"""
from crewai.tools import tool


# ── GitHub mocks ──────────────────────────────────────────────────────────────

@tool("Get PR Diff")
def mock_get_pr_diff(repo_full_name: str, pr_number: int) -> str:
    """Fetch the unified diff for a GitHub pull request."""
    return f"""--- a/src/auth/login.py (+42 / -18)
@@ -10,7 +10,7 @@ class LoginHandler:
-    def authenticate(self, user, password):
+    def authenticate(self, user: str, password: str) -> bool:
         if not user or not password:
-            return False
+            raise ValueError("user and password must not be empty")
         db_user = self.db.find(user)
         if db_user is None:
             return False
-        return bcrypt.check_password_hash(db_user.password, password)
+        return bcrypt.checkpw(password.encode(), db_user.password)

--- a/tests/test_auth.py (+5 / -0)
@@ -22,0 +23,5 @@ class TestLogin:
+    def test_authenticate_empty_password_raises(self):
+        handler = LoginHandler(db=MockDB())
+        with pytest.raises(ValueError):
+            handler.authenticate("alice", "")
+

--- a/src/utils/cache.py (+80 / -3)
@@ -1,3 +1,83 @@
+import redis
+import json
+
+CACHE_TTL = 300  # 5 minutes — no config, hardcoded
+
+def get_cached(key):
+    r = redis.Redis()   # no connection pooling
+    val = r.get(key)
+    return json.loads(val) if val else None
+
+def set_cached(key, value):
+    r = redis.Redis()   # new connection every call — potential leak
+    r.setex(key, CACHE_TTL, json.dumps(value))
"""


@tool("Get PR Checks")
def mock_get_pr_checks(repo_full_name: str, pr_number: int) -> str:
    """Return the CI check results for the HEAD commit of a pull request."""
    return """ci/lint: status=completed conclusion=success
ci/unit-tests: status=completed conclusion=success
ci/integration-tests: status=completed conclusion=failure
ci/security-scan: status=completed conclusion=success
ci/build: status=completed conclusion=failure"""


@tool("Post PR Comment")
def mock_post_pr_comment(repo_full_name: str, pr_number: int, body: str) -> str:
    """Post a review comment on a GitHub pull request."""
    preview = body[:120].replace("\n", " ")
    return f"[MOCK] Comment posted to {repo_full_name}#{pr_number}: \"{preview}...\""


@tool("Get Workflow Run")
def mock_get_workflow_run(repo_full_name: str, run_id: int) -> str:
    """Fetch metadata for a specific GitHub Actions workflow run."""
    return f"""Run #{run_id}: Deploy to Production
Status: completed | Conclusion: failure
Triggered by: push on main
  Job 'build': success — failed steps: []
  Job 'test': failure — failed steps: [run-integration-tests(failure)]
  Job 'deploy': skipped — failed steps: []"""


@tool("Get Workflow Logs")
def mock_get_workflow_logs(repo_full_name: str, run_id: int) -> str:
    """Download and return the log text for a failed GitHub Actions workflow run."""
    return """=== 2_test/run-integration-tests.txt ===
2024-04-25T10:22:01Z  Running integration tests...
2024-04-25T10:22:03Z  Setting up test database...
2024-04-25T10:22:05Z  FAILED: ConnectionRefusedError: [Errno 111] Connection refused
2024-04-25T10:22:05Z    File "tests/integration/test_orders.py", line 44, in setUp
2024-04-25T10:22:05Z      self.db = psycopg2.connect(host="localhost", port=5432, dbname="testdb")
2024-04-25T10:22:05Z  Error: Process completed with exit code 1.
2024-04-25T10:22:05Z
2024-04-25T10:22:05Z  Test results: 0 passed, 1 error, 47 skipped
2024-04-25T10:22:05Z  Hint: Did you forget to start the postgres service in the workflow?"""


@tool("Create GitHub Issue")
def mock_create_github_issue(repo_full_name: str, title: str, body: str, labels: list = None) -> str:
    """Create a GitHub issue to track an incident or follow-up action."""
    return f"[MOCK] Issue created: https://github.com/{repo_full_name}/issues/999 — \"{title}\""


# ── Prometheus mocks ──────────────────────────────────────────────────────────

@tool("Query Prometheus Metric")
def mock_query_metric(promql: str) -> str:
    """Execute an instant PromQL query and return the result."""
    return f"""PromQL: {promql}
  {{"namespace": "production", "deployment": "api-server"}} => 87.4
  {{"namespace": "production", "deployment": "worker"}} => 43.1"""


@tool("Query Prometheus Range")
def mock_query_metric_range(promql: str, start: str, end: str, step: str = "60s") -> str:
    """Execute a range PromQL query and return a summary."""
    return f"""PromQL range [{start} → {end}]: {promql}
  Series: {{"deployment": "api-server", "namespace": "production"}}
  Min=62.1000  Max=94.8000  Avg=81.3500  Points=30"""


@tool("Get Active Alerts")
def mock_get_active_alerts(filter_labels: str = "") -> str:
    """Fetch currently firing alerts from Alertmanager."""
    return """[CRITICAL] HighCPUUsage — api-server CPU above 85% for 10+ minutes
[WARNING]  HighMemoryPressure — worker pod memory at 91% of limit
[CRITICAL] PodCrashLooping — api-server-7d4f9c8b6-xk2pq restarted 5 times in 15 minutes"""


# ── Kubernetes mocks ──────────────────────────────────────────────────────────

@tool("Get Deployment Status")
def mock_get_deployment_status(deployment_name: str) -> str:
    """Return the current status of a Kubernetes deployment."""
    return f"""Deployment: {deployment_name}
  Replicas: desired=3 ready=1 available=1
  Images: myrepo/api-server:v1.4.2"""


@tool("Get Pod Events")
def mock_get_pod_events(deployment_name: str) -> str:
    """Retrieve recent Kubernetes events related to pods in a deployment."""
    return f"""[Warning] BackOff: Back-off restarting failed container in pod api-server-7d4f9c8b6-xk2pq (count=5, last=2024-04-25T10:18:00Z)
[Warning] OOMKilled: Container api-server exceeded memory limit and was killed (count=3, last=2024-04-25T10:15:00Z)
[Normal] Pulling: Pulling image "myrepo/api-server:v1.4.2" (count=5, last=2024-04-25T10:12:00Z)
[Warning] Failed: Failed to pull image: rpc error: rate limit exceeded (count=2, last=2024-04-25T10:10:00Z)"""


@tool("Get Pod Logs")
def mock_get_pod_logs(pod_name: str, tail_lines: int = 100) -> str:
    """Fetch the last N lines of logs from a Kubernetes pod."""
    return f"""[api-server-7d4f9c8b6-xk2pq last {tail_lines} lines]
2024-04-25T10:17:55Z INFO  Starting api-server v1.4.2
2024-04-25T10:17:56Z INFO  Connecting to database...
2024-04-25T10:17:57Z ERROR Cannot allocate memory: malloc failed for 512MB cache pre-warm
2024-04-25T10:17:57Z ERROR Traceback (most recent call last):
2024-04-25T10:17:57Z ERROR   File "server/cache.py", line 88, in warm_cache
2024-04-25T10:17:57Z ERROR     self._cache = np.zeros((CACHE_SIZE,), dtype=np.float32)
2024-04-25T10:17:57Z ERROR MemoryError: Unable to allocate 512 MiB
2024-04-25T10:17:57Z FATAL OOM — exiting"""


@tool("Restart Pod")
def mock_restart_pod(deployment_name: str, approved: bool = False) -> str:
    """Trigger a rolling restart of all pods in a Kubernetes deployment."""
    if not approved:
        raise PermissionError(
            f"Action 'restart_pod' requires human approval. "
            "Set approved=True via the /approve endpoint before proceeding."
        )
    return f"[MOCK] Rolling restart triggered for deployment '{deployment_name}'."


@tool("Scale Deployment")
def mock_scale_deployment(deployment_name: str, replicas: int, approved: bool = False) -> str:
    """Scale a Kubernetes deployment to the specified replica count."""
    if replicas == 0 and not approved:
        raise PermissionError("scale_to_zero requires human approval.")
    return f"[MOCK] Deployment '{deployment_name}' scaled to {replicas} replicas."


@tool("Rollback Deployment")
def mock_rollback_deployment(deployment_name: str, approved: bool = False) -> str:
    """Roll back a Kubernetes deployment to its previous revision."""
    if not approved:
        raise PermissionError("rollback_deployment requires human approval.")
    return f"[MOCK] Rollback triggered for deployment '{deployment_name}'."
