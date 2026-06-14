import os
import json
import google.generativeai as genai

class GeminiClient:
    def __init__(self):
        # Retrieve API key from environment (either GEMINI_API_KEY or GOOGLE_API_KEY)
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Use gemini-1.5-flash for speed and reliability
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("[Gemini Client] Connected to Gemini API successfully.")
            except Exception as e:
                print(f"[Gemini Client] Failed to configure Gemini: {e}")
                self.model = None
        else:
            self.model = None
            print("[Gemini Client] No GEMINI_API_KEY or GOOGLE_API_KEY found. Using high-fidelity heuristic fallback engine.")

    def generate_prompt(self, query, logs, metrics, events, cost):
        prompt = f"""
You are the "Kubernetes Incident Commander Agent", an expert platform engineer and SRE.
A production incident has occurred, and the user is asking: "{query}".

You have run four parallel subagents (Logs Agent, Metrics Agent, Events Agent, Cost Agent) which returned the following raw data:

--- LOGS AGENT ---
Success: {logs.get('success')}
Message: {logs.get('message')}
Key Errors Found: {json.dumps(logs.get('data', {}).get('errors', []))}
Sample Logs:
{chr(10).join(logs.get('data', {}).get('logs', [])[-15:])}

--- METRICS AGENT ---
Success: {metrics.get('success')}
Message: {metrics.get('message')}
Limits/Requests: {json.dumps(metrics.get('data', {}).get('limits', {}))} / {json.dumps(metrics.get('data', {}).get('requests', {}))}
Current Usage Data: {json.dumps(metrics.get('data', {}).get('metrics', []) or metrics.get('data', {}).get('current_usage', []))}

--- EVENTS AGENT ---
Success: {events.get('success')}
Message: {events.get('message')}
Termination Status: {json.dumps(events.get('data', {}).get('termination_status', {}))}
Recent Events:
{json.dumps(events.get('data', {}).get('events', [])[-10:])}

--- COST AGENT ---
Success: {cost.get('success')}
Message: {cost.get('message')}
Node Pool Status: {json.dumps(cost.get('data', {}).get('node_pool', {}))}
Remediation Options Evaluated:
{json.dumps(cost.get('data', {}).get('scenarios', []))}

------------------

Please generate a comprehensive, structured Root Cause Analysis (RCA) and remediation report in Markdown format. 

Your report must include:
1. **Incident Summary**: Brief, user-friendly description of what is failing and why.
2. **Timeline of Events**: Chronological order of events leading to the crash.
3. **Subagent Findings**:
    - **Logs Analysis**: Highlight specific stack traces or crash reasons.
    - **Metrics Correlation**: Analyze CPU and memory trends, and limits check.
    - **Kubernetes Events**: Correlate termination codes (e.g. exit code 137).
    - **Cost & Capacity Assessment**: Highlight the financial impact of scaling vs code fixes.
4. **Root Cause Analysis (RCA)**: Explain *why* it crashed. Distinguish between symptoms (restart) and cause (e.g. memory leak, JVM settings).
5. **Remediation Steps**:
    - Provide concrete CLI commands or YAML blocks to apply the recommended fixes (short-term and long-term).
    - Format command blocks as code blocks.
    - Mention the cost difference between options.

Be precise, highly technical yet readable, and actionable.
"""
        return prompt

    def analyze_incident(self, query, logs, metrics, events, cost, context=None):
        if self.model:
            try:
                prompt = self.generate_prompt(query, logs, metrics, events, cost)
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"[Gemini Client] Error calling Gemini API: {e}. Falling back...")
                # fall through to fallback
        
        # High-Fidelity Heuristic Fallback Report (Customized based on query and demo/live data)
        return self._generate_fallback_report(query, logs, metrics, events, cost, context)

    def _generate_fallback_report(self, query, logs, metrics, events, cost, context):
        if context is None:
            context = {}
        namespace = context.get("namespace", "production")
        pod_name = context.get("pod", "payment-processor-78cf4d89-x9w2")
        
        # Extract variables for fallback rendering
        termination_status = events.get('data', {}).get('termination_status', {})
        reason = termination_status.get('reason', 'OOMKilled')
        exit_code = termination_status.get('exit_code', 137)

        
        # Check if live or demo
        is_live = context.get("mode") == "live"

        if not is_live:
            # High-fidelity mock report
            return f"""# Incident Investigation Report: Pod Restarts in Namespace `production`

**Status**: 🔴 Unhealthy | **Involved Workload**: `deployment/payment-processor` | **Incident Commander ID**: `IC-2026-9852`

---

## 1. Incident Summary
The pod **`{pod_name}`** is crash-looping in the `production` namespace. The Incident Commander subagents have correlated logs, events, metrics, and cluster capacity to determine that the pod is failing due to resource starvation, specifically container memory limits exhaustion.

---

## 2. Incident Timeline
*   **16:15:00** - Pod scheduled to `node-1` and containers started.
*   **16:15:09** - `PaymentProcessorService` startup completed.
*   **16:16:00** - High incoming transaction load begins.
*   **16:16:05** - Memory warning triggered at 88% of limit (448MiB).
*   **16:16:12** - JVM throws `java.lang.OutOfMemoryError: Java heap space`.
*   **16:16:14** - Pod terminated with **Exit Code 137** (OOMKilled).
*   **16:16:15** - Kubernetes sets pod status to `CrashLoopBackOff`.

---

## 3. Subagent Correlated Findings

### 📋 Logs Agent
*   **Status**: Success ✅
*   **Findings**: Identified a critical heap space exhaustion event:
    ```
    ERROR [http-exec-4] java.lang.OutOfMemoryError: Java heap space
    FATAL [main] JVM crashed with exit code 137 (OOM Killed).
    ```
*   **Insight**: The JVM process is requesting memory that exceeds the container's allocation limit.

### 📈 Metrics Agent
*   **Status**: Success ✅
*   **Findings**: Pod memory consumption showed a classic linear memory leak pattern, climbing from **220MiB** to **510MiB** in under 11 minutes (peaking at **99.6%** of the **512MiB** limit). CPU remained stable between 15% and 50%, ruling out CPU throttling.
*   **Memory Chart Info**: Linear rise indicates non-reclaimed objects in the garbage collector, likely in the payment token parser.

### 🔔 Events Agent
*   **Status**: Success ✅
*   **Findings**: Pod status records show an explicit termination reason of `OOMKilled` with exit code `137` at `16:16:14`.
*   **Insight**: Exit code 137 indicates the container was forcefully terminated by the OS Out-Of-Memory Killer because it exceeded its cgroup memory limit of 512MiB.

### 💰 Cost Agent
*   **Status**: Success ✅
*   **Findings**:
    *   **Current Cluster Node Cost**: 3x `Standard_D4s_v5` nodes = **$420.00/month**.
    *   **Current Memory Headroom**: 5.5GB (88.5% allocation).
    *   **Remediation Option A (Scale resource limits to 1GiB)**: Will increase requested memory by 768MiB across 3 replicas. Since headroom is highly constrained, this triggers a node autoscale, adding 1 node: **+$140.00/month** (33% increase).
    *   **Remediation Option B (JVM Tuning within 512MiB)**: Adjusts heap ratios to prevent cgroup violation, utilizing existing node headroom: **+$0.00/month** (0% increase).

---

## 4. Root Cause Analysis (RCA)
The core root cause is that **the JVM heap configuration is not aligned with the Kubernetes container limits**.
Because no explicit `-Xmx` or `-XX:MaxRAMPercentage` flags were provided to the JVM startup arguments, the JVM calculated its heap limits based on default host memory guidelines (or outdated cgroup logic), allowing the heap to grow past the container's hard limit of **512MiB**.
When memory usage surged under transaction load, the JVM attempted to claim more heap, prompting the Linux kernel to send `SIGKILL` (exit code 137) to the process.

---

## 5. Remediation Steps

### Option A: Apply JVM Heap Constraints (Recommended - Save $140/mo)
Modify the deployment's environment variables to configure the JVM garbage collector and restrict memory usage to **75%** of the cgroup limits. This forces Java garbage collection to trigger before the container is OOMKilled by Kubernetes.

Apply the following patch to the deployment:

```bash
kubectl patch deployment payment-processor -n production --patch '
spec:
  template:
    spec:
      containers:
      - name: payment-processor
        env:
        - name: JAVA_TOOL_OPTIONS
          value: "-XX:+UseG1GC -XX:MaxRAMPercentage=75.0"
'
```

### Option B: Scale Container Memory Limits (If load demands it)
If the JVM requires more than 512MiB memory to function under peak traffic, scale the limits to **1GiB** and requests to **512MiB**.

```bash
kubectl set resources deployment payment-processor -n production \\
  --limits=memory=1Gi,cpu=1 \\
  --requests=memory=512Mi,cpu=500m
```
*Note: This will likely trigger a node autoscale in the cluster, adding **$140.00/month** to the infrastructure bill.*
"""
        else:
            # Custom live report
            errors_str = "\n".join([f"* `{err}`" for err in logs.get('data', {}).get('errors', [])])
            if not errors_str:
                errors_str = "* No obvious errors found in the inspected logs."

            # Determine specific RCA and Fixes based on reason
            if reason in ["ImagePullBackOff", "ErrImagePull", "InvalidImageName"]:
                rca_details = f"The pod is failing because the container runtime cannot pull the configured image.\nThe exact state reported by Kubernetes is **`{reason}`**.\n\nThis typically occurs when:\n1. The image name or tag has a typo.\n2. The image tag does not exist in the remote container registry.\n3. The cluster does not have permissions to access the registry (missing `imagePullSecrets`)."
                suggested_fixes = f"1. **Verify the configured image name and tag**:\n   Check the exact image name configured in the deployment:\n   ```bash\n   kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].image}}'\n   ```\n2. **Inspect the container registry**:\n   Verify that the registry path and tag actually exist.\n3. **Update to the correct image**:\n   Fix the image or tag using `kubectl set image`:\n   ```bash\n   kubectl set image deployment/<deployment-name> <container-name>=<correct-image-name>:<correct-tag> -n {namespace}\n   ```\n4. **Add registry pull credentials**:\n   If the image is in a private registry, make sure you configure your `imagePullSecrets` in the deployment specifications."
            elif reason == "OOMKilled":
                rca_details = f"The container was forcefully terminated with exit code **137** because its memory usage exceeded the configured limits of **{metrics.get('data', {}).get('limits', {}).get('memory_mb', 'Unknown')} MiB**."
                suggested_fixes = f"1. **Increase memory limits**:\n   Scale the container resource limits:\n   ```bash\n   kubectl set resources deployment/<deployment-name> -n {namespace} --limits=memory=<new-limit>\n   ```\n2. **Tune application memory usage**:\n   Optimize GC parameters or runtime environment options (e.g. `JAVA_TOOL_OPTIONS` or `NODE_OPTIONS`)."
            else:
                rca_details = f"The container is currently in **`{reason}`** status (Exit Code: {exit_code}).\nIf the exit code is non-zero, this points to an application startup crash or config issue. Please check the logs tab for stack traces."
                suggested_fixes = f"1. **Inspect container configuration**:\n   Check environment variables, volumes, and secret mounts.\n2. **Check application logs**:\n   Verify logs on the Logs panel to see if there are database connection timeouts or missing secrets."

            return f"""# Live Incident Investigation Report

**Namespace**: `{namespace}` | **Pod**: `{pod_name}` | **Mode**: Live Cluster Analysis

---

## 1. Incident Summary
The Incident Commander analyzed pod **`{pod_name}`** in namespace `{namespace}`. 
*   **Workload Status**: State: `{reason}` | Terminated: `{termination_status.get('terminated', False)}` | Exit Code: `{exit_code}`
*   **Log Context**: {logs.get('message', 'N/A')}

---

## 2. Correlated Subagent Findings

### 📋 Logs Agent
{logs.get('message')}
*   **Key Log Diagnostics**:
{errors_str}

### 📈 Metrics Agent
{metrics.get('message')}
*   **Resource Limits**: {json.dumps(metrics.get('data', {}).get('limits', {}))}
*   **Resource Requests**: {json.dumps(metrics.get('data', {}).get('requests', {}))}
*   **Current Usage**: {json.dumps(metrics.get('data', {}).get('current_usage', []))}

### 🔔 Events Agent
{events.get('message')}
*   **Lifecycle details**: Container status reason is '{reason}' with exit code {exit_code}.
*   **Total Namespace events inspected**: {len(events.get('data', {}).get('events', []))} events found.

### 💰 Cost Agent
{cost.get('message')}

---

## 3. Root Cause Analysis (RCA) & Summary
{rca_details}

---

## 4. Suggested Fixes
{suggested_fixes}
"""
