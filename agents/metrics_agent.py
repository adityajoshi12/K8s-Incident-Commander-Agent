import subprocess
import json
from agents.base import BaseAgent, AgentResult

class MetricsAgent(BaseAgent):
    def __init__(self):
        super().__init__("Metrics Agent")

    def run(self, context):
        mode = context.get("mode", "demo")
        namespace = context.get("namespace", "production")
        pod_name = context.get("pod", "payment-processor-78cf4d89-x9w2")

        self.log(f"Running in {mode} mode for pod {pod_name} in namespace {namespace}")

        if mode == "demo":
            # 15-minute timeseries showing memory leak leading to crash
            timestamps = [f"16:{m:02d}" for m in range(5, 21)]
            memory_mb = [220, 240, 265, 290, 310, 335, 360, 390, 420, 445, 470, 495, 510, 15, 20, 25]
            cpu_cores = [0.15, 0.18, 0.22, 0.20, 0.25, 0.28, 0.32, 0.35, 0.33, 0.40, 0.45, 0.48, 0.50, 0.02, 0.05, 0.08]
            
            memory_limit = 512  # MB
            cpu_limit = 1.0     # core
            
            metrics = []
            for t, mem, cpu in zip(timestamps, memory_mb, cpu_cores):
                metrics.append({
                    "timestamp": t,
                    "memory_usage_mb": mem,
                    "memory_pct": round((mem / memory_limit) * 100, 2),
                    "cpu_usage_cores": cpu,
                    "cpu_pct": round((cpu / cpu_limit) * 100, 2)
                })

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "metrics": metrics,
                    "limits": {"memory_mb": memory_limit, "cpu_cores": cpu_limit},
                    "peak_memory_pct": 99.6
                },
                message=f"Detected critical memory escalation spiking to 510MB/512MB (99.6% limit) followed by a sudden collapse, confirming memory-induced crash."
            )
        else:
            # Live mode: check current utilization using kubectl top or resource specs
            try:
                # Get pod resource limits and requests from pod spec
                limit_cmd = ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"]
                limit_res = subprocess.run(limit_cmd, capture_output=True, text=True, timeout=10)
                
                limits = {"memory_mb": 0, "cpu_cores": 0}
                requests = {"memory_mb": 0, "cpu_cores": 0}
                container_names = []
                container_images = []
                pod_status = "Unknown"
                pod_phase = "Unknown"
                node_name = ""
                
                if limit_res.returncode == 0:
                    pod_json = json.loads(limit_res.stdout)
                    pod_phase = pod_json.get("status", {}).get("phase", "Unknown")
                    node_name = pod_json.get("spec", {}).get("nodeName", "")
                    
                    containers = pod_json.get("spec", {}).get("containers", [])
                    for c in containers:
                        container_names.append(c.get("name", "unknown"))
                        container_images.append(c.get("image", "unknown"))
                        res = c.get("resources", {})
                        
                        # Parse memory limit
                        mem_limit = res.get("limits", {}).get("memory", "")
                        limits["memory_mb"] += self._parse_memory(mem_limit)
                        
                        # Parse CPU limit
                        cpu_limit = res.get("limits", {}).get("cpu", "")
                        limits["cpu_cores"] += self._parse_cpu(cpu_limit)

                        # Parse requests
                        mem_req = res.get("requests", {}).get("memory", "")
                        requests["memory_mb"] += self._parse_memory(mem_req)
                        
                        cpu_req = res.get("requests", {}).get("cpu", "")
                        requests["cpu_cores"] += self._parse_cpu(cpu_req)
                    
                    # Get container statuses for state info
                    container_statuses = pod_json.get("status", {}).get("containerStatuses", [])
                    for cs in container_statuses:
                        state = cs.get("state", {})
                        if "running" in state:
                            pod_status = "Running"
                        elif "waiting" in state:
                            pod_status = state["waiting"].get("reason", "Waiting")
                        elif "terminated" in state:
                            pod_status = state["terminated"].get("reason", "Terminated")

                # Try getting current usage from metrics-server
                usage = []
                metrics_server_available = False
                metrics_error = ""
                
                # Try with --containers first
                top_cmd = ["kubectl", "top", "pod", pod_name, "-n", namespace, "--containers", "--no-headers"]
                top_res = subprocess.run(top_cmd, capture_output=True, text=True, timeout=10)
                
                if top_res.returncode == 0 and top_res.stdout.strip():
                    metrics_server_available = True
                    lines = top_res.stdout.strip().splitlines()
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 4:
                            c_name = parts[1]
                            cpu_val = parts[2]
                            mem_val = parts[3]
                            
                            usage.append({
                                "container": c_name,
                                "cpu_cores": self._parse_cpu(cpu_val),
                                "memory_mb": self._parse_memory(mem_val)
                            })
                else:
                    # Try without --containers flag
                    top_cmd2 = ["kubectl", "top", "pod", pod_name, "-n", namespace, "--no-headers"]
                    top_res2 = subprocess.run(top_cmd2, capture_output=True, text=True, timeout=10)
                    
                    if top_res2.returncode == 0 and top_res2.stdout.strip():
                        metrics_server_available = True
                        lines = top_res2.stdout.strip().splitlines()
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 3:
                                cpu_val = parts[1]
                                mem_val = parts[2]
                                usage.append({
                                    "container": container_names[0] if container_names else "main",
                                    "cpu_cores": self._parse_cpu(cpu_val),
                                    "memory_mb": self._parse_memory(mem_val)
                                })
                    else:
                        metrics_error = top_res.stderr.strip() if top_res.stderr else "Metrics API not available"

                # Build summary message
                has_limits = limits["memory_mb"] > 0 or limits["cpu_cores"] > 0
                has_usage = len(usage) > 0
                
                msg_parts = []
                if has_usage:
                    for u in usage:
                        msg_parts.append(f"Container '{u['container']}': {u['memory_mb']}Mi memory, {u['cpu_cores']} CPU cores")
                    msg = "Live resource usage: " + "; ".join(msg_parts) + "."
                elif has_limits:
                    msg = f"Retrieved resource specs (Limits: {limits['memory_mb']}Mi Memory, {limits['cpu_cores']} CPU). Metrics-server unavailable for live usage data."
                else:
                    msg = "No resource limits/requests configured on this pod. Metrics-server unavailable for live usage data."

                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    data={
                        "limits": limits,
                        "requests": requests,
                        "current_usage": usage,
                        "metrics_server_available": metrics_server_available,
                        "metrics_error": metrics_error,
                        "container_names": container_names,
                        "container_images": container_images,
                        "pod_phase": pod_phase,
                        "pod_status": pod_status,
                        "node_name": node_name
                    },
                    message=msg
                )
            except Exception as e:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={"error": str(e)},
                    message=f"Error querying live pod metrics: {str(e)}"
                )

    @staticmethod
    def _parse_memory(val):
        """Parse Kubernetes memory strings like 512Mi, 1Gi, 100Ki, 1000000 to MiB."""
        if not val:
            return 0
        val = str(val).strip()
        try:
            if val.endswith("Ki"):
                return round(int(val.replace("Ki", "")) / 1024, 1)
            elif val.endswith("Mi"):
                return int(val.replace("Mi", ""))
            elif val.endswith("Gi"):
                return int(val.replace("Gi", "")) * 1024
            elif val.endswith("Ti"):
                return int(val.replace("Ti", "")) * 1024 * 1024
            elif val.isdigit():
                # Plain bytes
                return round(int(val) / (1024 * 1024), 1)
            else:
                return 0
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_cpu(val):
        """Parse Kubernetes CPU strings like 500m, 1, 0.5 to cores."""
        if not val:
            return 0.0
        val = str(val).strip()
        try:
            if val.endswith("m"):
                return round(int(val.replace("m", "")) / 1000.0, 3)
            elif val.endswith("n"):
                return round(int(val.replace("n", "")) / 1_000_000_000.0, 6)
            else:
                return round(float(val), 3)
        except (ValueError, TypeError):
            return 0.0

