import subprocess
from agents.base import BaseAgent, AgentResult

class LogsAgent(BaseAgent):
    def __init__(self):
        super().__init__("Logs Agent")

    def run(self, context):
        mode = context.get("mode", "demo")
        namespace = context.get("namespace", "production")
        pod_name = context.get("pod", "payment-processor-78cf4d89-x9w2")
        container = context.get("container")

        self.log(f"Running in {mode} mode for pod {pod_name} in namespace {namespace}")

        if mode == "demo":
            # High-fidelity simulated log output showing OutOfMemory crash
            logs = [
                "2026-06-12 16:15:02.124 INFO [main] Starting PaymentProcessorService...",
                "2026-06-12 16:15:05.412 INFO [main] Connecting to postgres-db.production.svc.cluster.local:5432...",
                "2026-06-12 16:15:07.899 INFO [main] Connection established. Initializing connection pool.",
                "2026-06-12 16:15:09.112 INFO [main] PaymentProcessorService started successfully on port 8080.",
                "2026-06-12 16:16:00.000 INFO [http-exec-1] Processing payment token: tok_87fa83d...",
                "2026-06-12 16:16:05.000 WARN [http-exec-3] Memory usage high: 88% of max limit (512MB).",
                "2026-06-12 16:16:10.000 INFO [http-exec-4] Processing payment token: tok_98fa22b...",
                "2026-06-12 16:16:12.115 ERROR [http-exec-4] java.lang.OutOfMemoryError: Java heap space",
                "2026-06-12 16:16:12.116 ERROR [http-exec-4] Dumping heap to java_pid1.hprof...",
                "2026-06-12 16:16:14.000 FATAL [main] JVM crashed with exit code 137 (OOM Killed)."
            ]
            found_errors = [
                "java.lang.OutOfMemoryError: Java heap space",
                "JVM crashed with exit code 137 (OOM Killed)"
            ]
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"logs": logs, "errors": found_errors},
                message="Identified JVM heap space exhaustion and exit code 137 (OOM Killed)."
            )
        else:
            # Live mode: invoke kubectl logs to get the container logs
            try:
                cmd = ["kubectl", "logs", pod_name, "-n", namespace, "--tail=200"]
                if container:
                    cmd.extend(["-c", container])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    return AgentResult(
                        agent_name=self.name,
                        success=False,
                        data={"error": result.stderr},
                        message=f"Failed to fetch live logs: {result.stderr.strip()}"
                    )
                
                logs_list = result.stdout.splitlines()
                errors = []
                for line in logs_list:
                    lower_line = line.lower()
                    if "error" in lower_line or "exception" in lower_line or "fatal" in lower_line or "oom" in lower_line or "panic" in lower_line:
                        errors.append(line)

                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    data={"logs": logs_list, "errors": errors[:20]},
                    message=f"Successfully fetched {len(logs_list)} lines of live logs. Found {len(errors)} potential error/exception lines."
                )
            except Exception as e:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={"error": str(e)},
                    message=f"Exception encountered while fetching live logs: {str(e)}"
                )
