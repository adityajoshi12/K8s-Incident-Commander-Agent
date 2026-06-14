import subprocess
import json
from agents.base import BaseAgent, AgentResult

class EventsAgent(BaseAgent):
    def __init__(self):
        super().__init__("Events Agent")

    def run(self, context):
        mode = context.get("mode", "demo")
        namespace = context.get("namespace", "production")
        pod_name = context.get("pod", "payment-processor-78cf4d89-x9w2")

        self.log(f"Running in {mode} mode for pod {pod_name} in namespace {namespace}")

        if mode == "demo":
            events = [
                {
                    "time": "16:15:00",
                    "type": "Normal",
                    "reason": "Scheduled",
                    "object": f"pod/{pod_name}",
                    "message": f"Successfully assigned {namespace}/{pod_name} to node-1"
                },
                {
                    "time": "16:15:02",
                    "type": "Normal",
                    "reason": "Pulled",
                    "object": f"pod/{pod_name}",
                    "message": "Container image \"payment-processor:v2.4.1\" already present on machine"
                },
                {
                    "time": "16:15:02",
                    "type": "Normal",
                    "reason": "Created",
                    "object": f"pod/{pod_name}",
                    "message": "Created container payment-processor"
                },
                {
                    "time": "16:15:03",
                    "type": "Normal",
                    "reason": "Started",
                    "object": f"pod/{pod_name}",
                    "message": "Started container payment-processor"
                },
                {
                    "time": "16:16:14",
                    "type": "Warning",
                    "reason": "Killing",
                    "object": f"pod/{pod_name}",
                    "message": "Stopping container payment-processor"
                },
                {
                    "time": "16:16:15",
                    "type": "Warning",
                    "reason": "BackOff",
                    "object": f"pod/{pod_name}",
                    "message": f"Back-off restarting failed container payment-processor in pod {pod_name}_{namespace}"
                }
            ]
            
            # Highlight termination status
            termination_status = {
                "terminated": True,
                "reason": "OOMKilled",
                "exit_code": 137,
                "started_at": "16:15:03",
                "finished_at": "16:16:14"
            }

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"events": events, "termination_status": termination_status},
                message="Identified explicit OOMKilled (Exit Code 137) warning events and container back-off states."
            )
        else:
            # Live mode: check actual pod events
            try:
                # 1. Check pod status description for termination reason
                status_cmd = ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"]
                status_res = subprocess.run(status_cmd, capture_output=True, text=True, timeout=10)
                
                termination_status = {"terminated": False, "reason": "Unknown", "exit_code": 0}
                
                if status_res.returncode == 0:
                    pod_json = json.loads(status_res.stdout)
                    container_statuses = pod_json.get("status", {}).get("containerStatuses", [])
                    for cs in container_statuses:
                        state = cs.get("state", {})
                        terminated = state.get("terminated")
                        waiting = state.get("waiting")
                        last_state = cs.get("lastState", {})
                        last_terminated = last_state.get("terminated")
                        
                        if terminated:
                            termination_status = {
                                "terminated": True,
                                "reason": terminated.get("reason", "Unknown"),
                                "exit_code": terminated.get("exitCode", 0),
                                "started_at": terminated.get("startedAt", ""),
                                "finished_at": terminated.get("finishedAt", "")
                            }
                        elif waiting:
                            termination_status = {
                                "terminated": False,
                                "reason": waiting.get("reason", "Unknown"),
                                "exit_code": 0,
                                "message": waiting.get("message", "")
                            }
                        elif last_terminated:
                            termination_status = {
                                "terminated": True,
                                "reason": last_terminated.get("reason", "Unknown"),
                                "exit_code": last_terminated.get("exitCode", 0),
                                "started_at": last_terminated.get("startedAt", ""),
                                "finished_at": last_terminated.get("finishedAt", "")
                            }

                # 2. Get events relating to this pod
                event_cmd = [
                    "kubectl", "get", "events", "-n", namespace,
                    "--field-selector", f"involvedObject.name={pod_name}",
                    "-o", "json"
                ]
                event_res = subprocess.run(event_cmd, capture_output=True, text=True, timeout=10)
                
                events = []
                if event_res.returncode == 0 and event_res.stdout.strip():
                    event_list = json.loads(event_res.stdout).get("items", [])
                    for e in event_list:
                        events.append({
                            "time": e.get("lastTimestamp") or e.get("eventTime") or "unknown",
                            "type": e.get("type", "Normal"),
                            "reason": e.get("reason", "Unknown"),
                            "object": f"{e.get('involvedObject', {}).get('kind', 'Pod')}/{e.get('involvedObject', {}).get('name', '')}",
                            "message": e.get("message", "")
                        })

                # If no direct pod events, get namespace events sorted by time
                if not events:
                    ns_event_cmd = [
                        "kubectl", "get", "events", "-n", namespace,
                        "--sort-by=.metadata.creationTimestamp", "-o", "json"
                    ]
                    ns_event_res = subprocess.run(ns_event_cmd, capture_output=True, text=True, timeout=10)
                    if ns_event_res.returncode == 0:
                        event_list = json.loads(ns_event_res.stdout).get("items", [])
                        for e in event_list[-15:]:  # Last 15 events
                            events.append({
                                "time": e.get("lastTimestamp") or e.get("eventTime") or "unknown",
                                "type": e.get("type", "Normal"),
                                "reason": e.get("reason", "Unknown"),
                                "object": f"{e.get('involvedObject', {}).get('kind', 'Pod')}/{e.get('involvedObject', {}).get('name', '')}",
                                "message": e.get("message", "")
                            })

                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    data={"events": events, "termination_status": termination_status},
                    message=f"Retrieved container lifecycle state (Terminated: {termination_status['terminated']}, Reason: {termination_status['reason']}) and correlation events."
                )
            except Exception as e:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={"error": str(e)},
                    message=f"Error querying cluster events: {str(e)}"
                )
