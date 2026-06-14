import os
import subprocess
import json
from dotenv import load_dotenv

# Load variables from .env file before importing agents
load_dotenv()

from flask import Flask, request, jsonify, render_template, send_from_directory
from agents import IncidentCommanderOrchestrator

app = Flask(__name__, static_folder='static', template_folder='templates')
orchestrator = IncidentCommanderOrchestrator()


def get_k8s_server_version():
    """Detect the Kubernetes server version (major, minor) from the cluster."""
    try:
        cmd = ["kubectl", "version", "-o", "json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            version_info = json.loads(res.stdout)
            server = version_info.get("serverVersion", {})
            major = int(server.get("major", "1").strip("+"))
            # Minor can contain trailing chars like "33+" in some distros
            minor_raw = server.get("minor", "0").strip("+")
            minor = int(''.join(c for c in minor_raw if c.isdigit()) or "0")
            return (major, minor)
    except Exception:
        pass
    return (1, 0)  # Unknown, assume old


def supports_in_place_resize():
    """Check if the cluster supports In-Place Pod Vertical Scaling.
    
    - Alpha in v1.27 (feature gate required)
    - Beta in v1.33 (enabled by default)
    - GA/Stable in v1.35
    
    We target v1.33+ since the feature gate is on by default from beta.
    """
    major, minor = get_k8s_server_version()
    return major >= 1 and minor >= 33


# In-memory store for demo mode pod states so they can be "remediated" interactively
DEMO_PODS = [
    {
        "namespace": "production",
        "name": "payment-processor-78cf4d89-x9w2",
        "ready": "0/1",
        "status": "CrashLoopBackOff",
        "restarts": 14,
        "age": "2h",
        "cpu": "150m",
        "memory": "510Mi"
    },
    {
        "namespace": "production",
        "name": "payment-processor-78cf4d89-y2w1",
        "ready": "1/1",
        "status": "Running",
        "restarts": 0,
        "age": "2h",
        "cpu": "110m",
        "memory": "240Mi"
    },
    {
        "namespace": "production",
        "name": "payment-processor-78cf4d89-z4k5",
        "ready": "1/1",
        "status": "Running",
        "restarts": 0,
        "age": "2h",
        "cpu": "130m",
        "memory": "250Mi"
    },
    {
        "namespace": "production",
        "name": "postgres-db-59cf48-j29w",
        "ready": "1/1",
        "status": "Running",
        "restarts": 0,
        "age": "12d",
        "cpu": "220m",
        "memory": "1.2Gi"
    },
    {
        "namespace": "production",
        "name": "frontend-84cfdf-92kl",
        "ready": "1/1",
        "status": "Running",
        "restarts": 0,
        "age": "4d",
        "cpu": "45m",
        "memory": "128Mi"
    }
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/namespaces', methods=['GET'])
def get_namespaces():
    mode = request.args.get("mode", "live")
    if mode == "demo":
        return jsonify(["production", "staging", "development"])
    else:
        try:
            result = subprocess.run(["kubectl", "get", "ns", "-o", "json"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                ns_data = json.loads(result.stdout)
                ns_list = [item["metadata"]["name"] for item in ns_data.get("items", [])]
                return jsonify(ns_list)
            return jsonify(["default"])
        except Exception as e:
            return jsonify(["default", f"error: {str(e)}"])

import datetime

def parse_age(creation_timestamp):
    if not creation_timestamp or creation_timestamp == "unknown":
        return "unknown"
    try:
        # e.g., "2026-06-12T16:15:00Z"
        ts_str = creation_timestamp.replace("Z", "")
        if "." in ts_str:
            ts_str = ts_str.split(".")[0]
        creation_time = datetime.datetime.fromisoformat(ts_str)
        now = datetime.datetime.utcnow()
        diff = now - creation_time
        
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d"
        if hours > 0:
            return f"{hours}h"
        return f"{minutes}m"
    except Exception:
        return creation_timestamp

def get_pod_status_from_json(pod_item):
    status_obj = pod_item.get("status", {})
    phase = status_obj.get("phase", "Unknown")
    
    # Check if pod is being deleted
    metadata = pod_item.get("metadata", {})
    if "deletionTimestamp" in metadata:
        return "Terminating"
        
    # Check init containers
    init_statuses = status_obj.get("initContainerStatuses", [])
    for cs in init_statuses:
        state = cs.get("state", {})
        if "waiting" in state:
            return f"Init:{state['waiting'].get('reason', 'Waiting')}"
        elif "terminated" in state:
            if state["terminated"].get("exitCode", 0) != 0:
                return f"Init:Error"
                
    # Check regular containers
    container_statuses = status_obj.get("containerStatuses", [])
    
    # Check waiting reasons (CrashLoopBackOff, ImagePullBackOff, etc.)
    for cs in container_statuses:
        state = cs.get("state", {})
        if "waiting" in state:
            return state["waiting"].get("reason", "Waiting")
            
    # Check terminated reasons (Error, Completed, etc.)
    for cs in container_statuses:
        state = cs.get("state", {})
        if "terminated" in state:
            reason = state["terminated"].get("reason")
            if reason:
                return reason
            exit_code = state["terminated"].get("exitCode", 0)
            if exit_code != 0:
                return f"ExitCode:{exit_code}"
                
    return phase

@app.route('/api/pods', methods=['GET'])
def get_pods():
    mode = request.args.get("mode", "live")
    ns = request.args.get("namespace", "default")
    
    if mode == "demo":
        # Filter mock pods by namespace
        if ns == "production":
            return jsonify(DEMO_PODS)
        elif ns == "staging":
            return jsonify([
                {"namespace": "staging", "name": "payment-processor-stg-55f6", "ready": "1/1", "status": "Running", "restarts": 0, "age": "5d"},
                {"namespace": "staging", "name": "frontend-stg-33a1", "ready": "1/1", "status": "Running", "restarts": 0, "age": "5d"}
            ])
        else:
            return jsonify([
                {"namespace": "development", "name": "sandbox-pod-1", "ready": "1/1", "status": "Running", "restarts": 1, "age": "18h"}
            ])
    else:
        try:
            cmd = ["kubectl", "get", "pods", "-n", ns, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                pods_data = json.loads(result.stdout)
                pod_list = []
                for item in pods_data.get("items", []):
                    status_obj = item.get("status", {})
                    container_statuses = status_obj.get("containerStatuses", [])
                    restarts = sum(cs.get("restartCount", 0) for cs in container_statuses)
                    
                    ready_count = sum(1 for cs in container_statuses if cs.get("ready", False))
                    total_containers = len(container_statuses)
                    ready_str = f"{ready_count}/{total_containers}" if total_containers > 0 else "0/0"
                    
                    pod_status = get_pod_status_from_json(item)
                    age_str = parse_age(item["metadata"].get("creationTimestamp", "unknown"))
                    
                    pod_list.append({
                        "namespace": ns,
                        "name": item["metadata"]["name"],
                        "ready": ready_str,
                        "status": pod_status,
                        "restarts": restarts,
                        "age": age_str
                    })
                return jsonify(pod_list)
            return jsonify([])
        except Exception as e:
            return jsonify([{"name": f"error: {str(e)}", "status": "Failed", "ready": "0/0", "restarts": 0}])

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json or {}
    query = data.get("query", "Why are my pods restarting?")
    mode = data.get("mode", "live")
    namespace = data.get("namespace", "default")
    pod = data.get("pod", "")
    
    # Run orchestrator
    context = {
        "mode": mode,
        "namespace": namespace,
        "pod": pod
    }
    
    analysis_result = orchestrator.run_investigation(query, context)
    return jsonify(analysis_result)

@app.route('/api/apply-fix', methods=['POST'])
def apply_fix():
    data = request.json or {}
    option = data.get("option", "B")  # Option A: Scale, Option B: JVM GC Patch
    mode = data.get("mode", "live")
    namespace = data.get("namespace", "default")
    pod = data.get("pod", "")

    if mode == "demo":
        # Modify the demo pod state in-memory to reflect a fix!
        global DEMO_PODS
        for p in DEMO_PODS:
            if p["name"] == pod:
                p["status"] = "Running"
                p["ready"] = "1/1"
                p["restarts"] = 0
                p["age"] = "Just now (remediated)"
                p["memory"] = "384Mi" if option == "B" else "512Mi" # GC optimization reduces memory, scale-up allows full limit
        
        return jsonify({
            "success": True,
            "message": f"Successfully applied Remediation Option {option} in Demo Mode! Pod '{pod}' has restarted with correct memory allocation and is now healthy.",
            "dry_run": False
        })
    else:
        # Live mode: perform dry-run and execute command
        try:
            # Fallback values
            workload_kind = "pod"
            workload_name = pod
            container_name = "app"
            
            try:
                cmd = ["kubectl", "get", "pod", pod, "-n", namespace, "-o", "json"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    pod_json = json.loads(res.stdout)
                    containers = pod_json.get("spec", {}).get("containers", [])
                    if containers:
                        container_name = containers[0].get("name", container_name)
                    
                    owner_refs = pod_json.get("metadata", {}).get("ownerReferences", [])
                    if owner_refs:
                        ref = owner_refs[0]
                        ref_kind = ref.get("kind")
                        ref_name = ref.get("name")
                        
                        if ref_kind == "ReplicaSet":
                            # ReplicaSet is usually owned by a Deployment
                            workload_kind = "deployment"
                            workload_name = ref_name  # fallback
                            try:
                                rs_cmd = ["kubectl", "get", "replicaset", ref_name, "-n", namespace, "-o", "json"]
                                rs_res = subprocess.run(rs_cmd, capture_output=True, text=True, timeout=3)
                                if rs_res.returncode == 0:
                                    rs_json = json.loads(rs_res.stdout)
                                    rs_owners = rs_json.get("metadata", {}).get("ownerReferences", [])
                                    if rs_owners:
                                        workload_name = rs_owners[0].get("name", ref_name)
                            except Exception:
                                # Fallback split logic
                                rs_parts = ref_name.split('-')
                                if len(rs_parts) >= 2:
                                    workload_name = "-".join(rs_parts[:-1])
                        elif ref_kind == "StatefulSet":
                            workload_kind = "statefulset"
                            workload_name = ref_name
                        elif ref_kind == "DaemonSet":
                            workload_kind = "daemonset"
                            workload_name = ref_name
                        else:
                            workload_kind = ref_kind.lower()
                            workload_name = ref_name
                    else:
                        # Standalone pod
                        workload_kind = "pod"
                        workload_name = pod
            except Exception:
                pass

            # Detect cluster version for in-place resize support
            can_resize = supports_in_place_resize()
            major, minor = get_k8s_server_version()
            version_note = f"(Detected cluster v{major}.{minor})"

            if option == "B":
                # Option B: JVM GC Patch (env var update)
                if workload_kind == "pod":
                    # Note: env vars are NOT part of the resize subresource -- they always require pod recreation
                    cmd_str = (
                        f"# {version_note}\n"
                        f"# Note: Environment variables cannot be updated in-place on running pods\n"
                        f"# (In-Place Resize only covers CPU/memory resources, not env vars).\n"
                        f"# To apply GC tuning, recreate the pod with the new env:\n\n"
                        f"kubectl get pod {pod} -n {namespace} -o yaml > /tmp/{pod}.yaml\n"
                        f"# Edit /tmp/{pod}.yaml and add under spec.containers[].env:\n"
                        f"#   - name: JAVA_TOOL_OPTIONS\n"
                        f"#     value: \"-XX:+UseG1GC -XX:MaxRAMPercentage=75.0\"\n"
                        f"kubectl delete pod {pod} -n {namespace}\n"
                        f"kubectl apply -f /tmp/{pod}.yaml"
                    )
                    msg = "GC Patch: Standalone pods must be recreated to update environment variables (env is not part of resize subresource)."
                else:
                    cmd_str = f"kubectl patch {workload_kind} {workload_name} -n {namespace} --patch '{{\"spec\":{{\"template\":{{\"spec\":{{\"containers\":[{{\"name\":\"{container_name}\",\"env\":[{{\"name\":\"JAVA_TOOL_OPTIONS\",\"value\":\"-XX:+UseG1GC -XX:MaxRAMPercentage=75.0\"}}]}}]}}}}}}}}}}'"
                    msg = "Dry-run: Generated patch script successfully."
            elif option == "ImageFix":
                # Option ImageFix: Update container image
                if workload_kind == "pod":
                    cmd_str = (
                        f"# {version_note}\n"
                        f"# To fix the image on a standalone pod, recreate with the correct image:\n\n"
                        f"kubectl get pod {pod} -n {namespace} -o yaml > /tmp/{pod}.yaml\n"
                        f"# Edit /tmp/{pod}.yaml - update spec.containers[].image to the correct image:tag\n"
                        f"kubectl delete pod {pod} -n {namespace}\n"
                        f"kubectl apply -f /tmp/{pod}.yaml"
                    )
                    msg = "Dry-run: Standalone pod image must be fixed via recreate. Export -> edit -> apply."
                else:
                    cmd_str = f"kubectl set image {workload_kind}/{workload_name} {container_name}=<correct-image-name>:<tag> -n {namespace}"
                    msg = "Dry-run: Generated image correction command successfully."
            else:
                # Option A: Resource limit scale-up
                if workload_kind == "pod":
                    if can_resize:
                        # K8s v1.33+ -- use In-Place Pod Vertical Scaling
                        cmd_str = (
                            f"# {version_note} -- In-Place Pod Vertical Scaling supported! [OK]\n"
                            f"# Resizing resources on running standalone pod without restart:\n\n"
                            f"kubectl patch pod {pod} -n {namespace} --subresource resize --patch '\n"
                            f"{{\"spec\":{{\"containers\":[{{\"name\":\"{container_name}\","
                            f"\"resources\":{{\"limits\":{{\"memory\":\"1Gi\",\"cpu\":\"1\"}},"
                            f"\"requests\":{{\"memory\":\"512Mi\",\"cpu\":\"500m\"}}}}}}]}}}}'"
                        )
                        msg = f"In-Place Resize (v{major}.{minor}): Generated kubectl patch --subresource resize command for standalone pod."
                    else:
                        # Older cluster -- must recreate
                        cmd_str = (
                            f"# {version_note} -- In-Place Resize NOT available (requires v1.33+)\n"
                            f"# Standalone pods must be recreated to change resource requests/limits.\n\n"
                            f"kubectl get pod {pod} -n {namespace} -o yaml > /tmp/{pod}.yaml\n"
                            f"# Edit /tmp/{pod}.yaml - update resources.limits and resources.requests\n"
                            f"# resources:\n"
                            f"#   limits:\n"
                            f"#     memory: 1Gi\n"
                            f"#     cpu: 1\n"
                            f"#   requests:\n"
                            f"#     memory: 512Mi\n"
                            f"#     cpu: 500m\n"
                            f"kubectl delete pod {pod} -n {namespace}\n"
                            f"kubectl apply -f /tmp/{pod}.yaml"
                        )
                        msg = f"Resource Scaling (v{major}.{minor}): Standalone pod requires recreate -- cluster does not support in-place resize."
                else:
                    cmd_str = f"kubectl set resources {workload_kind}/{workload_name} -n {namespace} --limits=memory=1Gi,cpu=1 --requests=memory=512Mi,cpu=500m --containers={container_name}"
                    msg = "Dry-run: Generated resource scaling command successfully."

            return jsonify({
                "success": True,
                "message": msg,
                "command": cmd_str,
                "dry_run": True
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Failed to execute remediation: {str(e)}",
                "dry_run": False
            })

if __name__ == '__main__':
    # Retrieve port from env or default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
