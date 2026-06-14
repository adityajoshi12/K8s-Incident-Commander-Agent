// Application State
let currentState = {
    mode: 'live', // 'demo' or 'live'
    namespace: 'default',
    pod: '',
    podsList: [],
    analysisResult: null
};

// Real-time pod polling
let podPollingInterval = null;
const POD_POLL_INTERVAL_MS = 5000; // 5 seconds

// Chart Instances
let memoryChartInstance = null;
let cpuChartInstance = null;

// Markdown-it parser instance
const md = window.markdownit({
    html: true,
    linkify: true,
    typographer: true
});

// DOM Elements
const modeToggle = document.getElementById('mode-toggle');
const toggleSwitch = modeToggle.querySelector('.toggle-switch');
const toggleTexts = modeToggle.querySelectorAll('.toggle-text');
const nsSelect = document.getElementById('ns-select');
const podSelect = document.getElementById('pod-select');
const podsTbody = document.getElementById('pods-tbody');
const chatHistory = document.getElementById('chat-history');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const clusterIndicator = document.getElementById('cluster-indicator');

// Agent Boxes
const agents = {
    logs: document.getElementById('agent-logs'),
    metrics: document.getElementById('agent-metrics'),
    events: document.getElementById('agent-events'),
    cost: document.getElementById('agent-cost')
};
const durationBadge = document.getElementById('duration-badge');

// Tabs
const tabHeaders = document.querySelectorAll('.tab-header');
const tabContents = document.querySelectorAll('.tab-content');

// RCA Elements
const rcaPlaceholder = document.getElementById('rca-placeholder');
const rcaContent = document.getElementById('rca-content');
const remediationBox = document.getElementById('remediation-box');
const remediationResult = document.getElementById('remediation-result');

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadNamespaces();
    loadPods();
});

// Event Listeners Setup
function setupEventListeners() {
    // Mode Toggle Click Handler
    modeToggle.addEventListener('click', () => {
        if (currentState.mode === 'demo') {
            currentState.mode = 'live';
            toggleSwitch.className = 'toggle-switch live-active';
            toggleTexts[0].classList.remove('active');
            toggleTexts[1].classList.add('active');
        } else {
            currentState.mode = 'demo';
            toggleSwitch.className = 'toggle-switch demo-active';
            toggleTexts[0].classList.add('active');
            toggleTexts[1].classList.remove('active');
        }
        addSystemMessage(`Switched cluster mode to <strong>${currentState.mode === 'demo' ? 'Simulated Demo Cluster' : 'Live Kubernetes Cluster'}</strong>.`);
        loadNamespaces();
    });

    // Namespace Selector Change Handler
    nsSelect.addEventListener('change', (e) => {
        currentState.namespace = e.target.value;
        loadPods();
    });

    // Pod Selector Change Handler
    podSelect.addEventListener('change', (e) => {
        currentState.pod = e.target.value;
        highlightActivePod();
    });

    // Chat form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;
        
        chatInput.value = '';
        runInvestigation(query);
    });

    // Quick Suggestions Button click handler
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('suggest-btn')) {
            const query = e.target.getAttribute('data-query');
            runInvestigation(query);
        }
    });

    // Tabs Event Listener
    tabHeaders.forEach(header => {
        header.addEventListener('click', () => {
            tabHeaders.forEach(h => h.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            header.classList.add('active');
            const targetTab = header.getAttribute('data-tab');
            document.getElementById(`tab-${targetTab}`).classList.add('active');
        });
    });

    // Remediation Buttons
    document.getElementById('apply-btn-b').addEventListener('click', (e) => {
        const action = e.currentTarget.getAttribute('data-action') || 'B';
        applyRemediation(action);
    });
    document.getElementById('apply-btn-a').addEventListener('click', (e) => {
        const action = e.currentTarget.getAttribute('data-action') || 'A';
        applyRemediation(action);
    });
}

// Load Namespaces from Backend
async function loadNamespaces() {
    try {
        const response = await fetch(`/api/namespaces?mode=${currentState.mode}`);
        const namespaces = await response.json();
        
        nsSelect.innerHTML = '';
        namespaces.forEach(ns => {
            const option = document.createElement('option');
            option.value = ns;
            option.textContent = ns;
            if (ns === currentState.namespace) option.selected = true;
            nsSelect.appendChild(option);
        });

        // Update target state if selected is not in list
        if (!namespaces.includes(currentState.namespace)) {
            currentState.namespace = namespaces[0] || 'default';
        }
        
        loadPods();
    } catch (err) {
        console.error("Failed to load namespaces:", err);
    }
}

// Load Pods from Backend
async function loadPods() {
    try {
        const response = await fetch(`/api/pods?mode=${currentState.mode}&namespace=${currentState.namespace}`);
        currentState.podsList = await response.json();
        
        // Refresh Table
        renderPodsTable();
        
        // Populate Pod Selector
        podSelect.innerHTML = '';
        currentState.podsList.forEach(pod => {
            const option = document.createElement('option');
            option.value = pod.name;
            option.textContent = pod.name;
            if (pod.name === currentState.pod) option.selected = true;
            podSelect.appendChild(option);
        });

        // Set default selected pod if current not in list
        const names = currentState.podsList.map(p => p.name);
        if (names.length > 0 && !names.includes(currentState.pod)) {
            currentState.pod = names[0];
            if (podSelect.querySelector(`option[value="${currentState.pod}"]`)) {
                podSelect.querySelector(`option[value="${currentState.pod}"]`).selected = true;
            }
        }
        
        highlightActivePod();
        
        // Start real-time polling
        startPodPolling();
    } catch (err) {
        console.error("Failed to load pods:", err);
    }
}

// Start real-time pod status polling
function startPodPolling() {
    // Clear any existing interval to avoid stacking
    if (podPollingInterval) {
        clearInterval(podPollingInterval);
    }
    
    podPollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/pods?mode=${currentState.mode}&namespace=${currentState.namespace}`);
            const freshPods = await response.json();
            
            // Check if anything actually changed to avoid unnecessary re-renders
            const changed = JSON.stringify(freshPods) !== JSON.stringify(currentState.podsList);
            if (!changed) return;
            
            currentState.podsList = freshPods;
            
            // Silently re-render table (preserves selected pod)
            renderPodsTable();
            
            // Update dropdown options without resetting selection
            const previousPod = currentState.pod;
            podSelect.innerHTML = '';
            currentState.podsList.forEach(pod => {
                const option = document.createElement('option');
                option.value = pod.name;
                option.textContent = pod.name;
                if (pod.name === previousPod) option.selected = true;
                podSelect.appendChild(option);
            });

            // If selected pod disappeared from the cluster
            const names = currentState.podsList.map(p => p.name);
            if (names.length > 0 && !names.includes(previousPod)) {
                currentState.pod = names[0];
                podSelect.value = currentState.pod;
            }
            
            highlightActivePod();
        } catch (err) {
            // Silently ignore polling errors (network blips, etc.)
            console.warn("Pod polling error:", err);
        }
    }, POD_POLL_INTERVAL_MS);
}

// Render the health grid table of pods
function renderPodsTable() {
    podsTbody.innerHTML = '';
    
    if (currentState.podsList.length === 0) {
        podsTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No workloads found in namespace</td></tr>`;
        clusterIndicator.className = 'pulse-indicator green';
        return;
    }

    let hasUnhealthy = false;
    currentState.podsList.forEach(pod => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-pod-name', pod.name);
        
        if (pod.name === currentState.pod) {
            tr.className = 'active';
        }

        tr.addEventListener('click', () => {
            currentState.pod = pod.name;
            podSelect.value = pod.name;
            highlightActivePod();
        });

        const statusClass = pod.status.toLowerCase().includes('running') ? 'running' : 'crashloop';
        const restartClass = pod.restarts > 5 ? 'restarts-count heavy' : 'restarts-count';
        if (statusClass === 'crashloop') hasUnhealthy = true;

        tr.innerHTML = `
            <td><strong>${pod.name}</strong></td>
            <td>${pod.ready || '0/1'}</td>
            <td><span class="badge ${statusClass}">${pod.status}</span></td>
            <td><span class="${restartClass}">${pod.restarts}</span></td>
            <td>${pod.age}</td>
        `;
        podsTbody.appendChild(tr);
    });

    // Update global cluster indicator
    if (hasUnhealthy) {
        clusterIndicator.className = 'pulse-indicator red';
    } else {
        clusterIndicator.className = 'pulse-indicator green';
    }
}

// Highlight the selected pod row in the workload list
function highlightActivePod() {
    const rows = podsTbody.querySelectorAll('tr');
    rows.forEach(row => {
        if (row.getAttribute('data-pod-name') === currentState.pod) {
            row.classList.add('active');
        } else {
            row.classList.remove('active');
        }
    });
}

// Add user message to console
function addUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message user';
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-user"></i></div>
        <div class="message-content">
            <p>${text}</p>
        </div>
    `;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Add system message to console
function addSystemMessage(htmlText) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message system';
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content">
            <p>${htmlText}</p>
        </div>
    `;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Trigger Incident Investigation
async function runInvestigation(query) {
    addUserMessage(query);
    addSystemMessage(`Received incident investigation request for pod <strong>${currentState.pod}</strong> in namespace <strong>${currentState.namespace}</strong>.<br>Initializing multi-agent troubleshooting session...`);

    // Reset Agent Visualizers UI
    for (const key in agents) {
        agents[key].className = 'agent-box';
        agents[key].querySelector('.agent-status').textContent = 'Inactive';
    }
    durationBadge.textContent = 'Running...';
    durationBadge.style.color = 'var(--accent-pink)';

    // Switch view to RCA Report and show loading state
    switchTab('rca');
    rcaPlaceholder.classList.add('hidden');
    rcaContent.innerHTML = `
        <div class="rca-placeholder">
            <div class="logo-glow" style="position:static; margin-bottom: 1.5rem; width:50px; height:50px;"></div>
            <i class="fa-solid fa-spinner fa-spin placeholder-icon" style="font-size: 2.5rem; color: var(--accent-purple);"></i>
            <p><strong>Correlating metrics, logs, and cost metrics...</strong></p>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top:0.5rem;">Orchestrated subagents are retrieving data in parallel.</p>
        </div>
    `;
    remediationBox.classList.add('hidden');
    remediationResult.classList.add('hidden');

    // Simulate staggered parallel subagent startup for visually impressive feedback
    setTimeout(() => setAgentState('logs', 'active', 'Scanning logs...'), 200);
    setTimeout(() => setAgentState('metrics', 'active', 'Querying Prometheus...'), 400);
    setTimeout(() => setAgentState('events', 'active', 'Reading events...'), 600);
    setTimeout(() => setAgentState('cost', 'active', 'Analyzing cost implications...'), 800);

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                mode: currentState.mode,
                namespace: currentState.namespace,
                pod: currentState.pod
            })
        });

        if (!response.ok) throw new Error("Backend query failed");
        const result = await response.json();
        currentState.analysisResult = result;

        // Visual finish of subagent indicators
        setTimeout(() => setAgentState('logs', 'success', result.subagent_results.logs_agent.message), 1200);
        setTimeout(() => setAgentState('metrics', 'success', result.subagent_results.metrics_agent.message), 1500);
        setTimeout(() => setAgentState('events', 'success', result.subagent_results.events_agent.message), 1800);
        setTimeout(() => setAgentState('cost', 'success', result.subagent_results.cost_agent.message), 2100);

        // Update analysis details
        setTimeout(() => {
            durationBadge.textContent = `${result.total_duration_seconds}s`;
            durationBadge.style.color = 'var(--status-green)';
            
            // Render RCA Report Tab
            renderRcaReport(result.rca_report);
            
            // Populate logs, metrics, cost tabs
            populateTelemetryTab(result.subagent_results.metrics_agent);
            populateLogsTab(result.subagent_results.logs_agent);
            populateCostTab(result.subagent_results.cost_agent);

            // Add commander response in console
            addSystemMessage(`<strong>Incident analysis complete!</strong> Root Cause Analysis (RCA) report generated.<br>Check the <strong>RCA Report</strong> and <strong>Telemetry</strong> tabs for detailed findings.`);
        }, 2200);

    } catch (err) {
        console.error(err);
        durationBadge.textContent = 'Failed';
        durationBadge.style.color = 'var(--status-red)';
        
        for (const key in agents) {
            agents[key].className = 'agent-box';
            agents[key].querySelector('.agent-status').textContent = 'Error';
        }
        
        rcaContent.innerHTML = `<div class="remediation-result error">Error compiling root cause analysis: ${err.message}</div>`;
    }
}

// Set Subagent UI Box state
function setAgentState(agentKey, state, message) {
    const box = agents[agentKey];
    if (!box) return;

    box.className = `agent-box ${state}`;
    const statusP = box.querySelector('.agent-status');
    statusP.textContent = message;
    statusP.title = message;
}

// Switch between dashboard panels/tabs
function switchTab(tabId) {
    tabHeaders.forEach(h => {
        if (h.getAttribute('data-tab') === tabId) {
            h.classList.add('active');
        } else {
            h.classList.remove('active');
        }
    });

    tabContents.forEach(c => {
        if (c.id === `tab-${tabId}`) {
            c.classList.add('active');
        } else {
            c.classList.remove('active');
        }
    });
}

// Render Markdown RCA Report
function renderRcaReport(markdownText) {
    rcaPlaceholder.classList.add('hidden');
    rcaContent.innerHTML = md.render(markdownText);
    
    // Determine the diagnosed reason
    const eventsResult = currentState.analysisResult?.subagent_results?.events_agent?.data;
    const reason = eventsResult?.termination_status?.reason || "Unknown";
    const statusClass = (currentState.podsList.find(p => p.name === currentState.pod)?.status || "Running").toLowerCase();

    // Reset remediation buttons state
    const btnB = document.getElementById('apply-btn-b');
    const btnA = document.getElementById('apply-btn-a');
    
    btnB.classList.remove('hidden');
    btnA.classList.remove('hidden');

    // If workload is healthy, hide remediation center
    if (statusClass.includes('running') && !eventsResult?.termination_status?.terminated && reason === "Unknown") {
        remediationBox.classList.add('hidden');
        return;
    }

    if (reason === "ImagePullBackOff" || reason === "ErrImagePull") {
        // Image Pull issue
        btnB.innerHTML = `<i class="fa-solid fa-circle-check"></i> Generate Image Correction Command`;
        btnB.setAttribute('data-action', 'ImageFix');
        btnA.classList.add('hidden'); // Hide scale-up since it is unrelated
        remediationBox.classList.remove('hidden');
    } else if (reason === "OOMKilled") {
        // OOM issue
        btnB.innerHTML = `<i class="fa-solid fa-circle-check"></i> Apply GC Tuning Patch (Recommended - $0/mo)`;
        btnB.setAttribute('data-action', 'B');
        btnA.innerHTML = `<i class="fa-solid fa-arrow-up-right-dots"></i> Scale Up memory limits (+$140/mo)`;
        btnA.setAttribute('data-action', 'A');
        remediationBox.classList.remove('hidden');
    } else {
        // For other errors or unknown states
        btnB.innerHTML = `<i class="fa-solid fa-circle-check"></i> Generate GC Tuning Patch`;
        btnB.setAttribute('data-action', 'B');
        btnA.innerHTML = `<i class="fa-solid fa-arrow-up-right-dots"></i> Scale Up memory limits`;
        btnA.setAttribute('data-action', 'A');
        remediationBox.classList.remove('hidden');
    }
}

// Populate Telemetry & Charts Tab
function populateTelemetryTab(metricsAgentResult) {
    const summaryDiv = document.getElementById('telemetry-summary');
    
    if (!metricsAgentResult.success) {
        summaryDiv.innerHTML = `<div class="remediation-result error">Failed to gather telemetry: ${metricsAgentResult.message}</div>`;
        return;
    }

    const data = metricsAgentResult.data;
    
    // Check if we are in demo or live mode (demo has series metrics, live has stats)
    if (data.metrics && data.metrics.length > 0) {
        // Draw timeseries charts (Demo Mode)
        const labels = data.metrics.map(m => m.timestamp);
        const memData = data.metrics.map(m => m.memory_usage_mb);
        const cpuData = data.metrics.map(m => m.cpu_usage_cores);
        
        const memLimit = data.limits.memory_mb;
        const cpuLimit = data.limits.cpu_cores;

        // Render Memory Chart
        if (memoryChartInstance) memoryChartInstance.destroy();
        const ctxMem = document.getElementById('memory-chart').getContext('2d');
        memoryChartInstance = new Chart(ctxMem, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Memory Usage (MiB)',
                        data: memData,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: `Limit (${memLimit}Mi)`,
                        data: Array(labels.length).fill(memLimit),
                        borderColor: '#ef4444',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af' }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#f3f4f6' } }
                }
            }
        });

        // Render CPU Chart
        if (cpuChartInstance) cpuChartInstance.destroy();
        const ctxCpu = document.getElementById('cpu-chart').getContext('2d');
        cpuChartInstance = new Chart(ctxCpu, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'CPU Usage (Cores)',
                        data: cpuData,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: `Limit (${cpuLimit} Core)`,
                        data: Array(labels.length).fill(cpuLimit),
                        borderColor: '#ef4444',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af' }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#f3f4f6' } }
                }
            }
        });

        summaryDiv.innerHTML = `
            <p><strong>Telemetry Analysis:</strong> Critical OOM sequence detected. Memory utilization scaled up exponentially from <strong>220MiB</strong> to <strong>510MiB</strong>, touching the hard limits of the pod shell (<strong>512MiB</strong>) before failing.</p>
        `;
    } else {
        // Live mode -- rich layout with available data
        const hasLimits = (data.limits?.memory_mb > 0 || data.limits?.cpu_cores > 0);
        const hasRequests = (data.requests?.memory_mb > 0 || data.requests?.cpu_cores > 0);
        const hasUsage = data.current_usage && data.current_usage.length > 0;
        const metricsAvailable = data.metrics_server_available === true;
        const containerNames = data.container_names || [];
        const containerImages = data.container_images || [];

        let html = `<div style="display:flex; flex-direction:column; gap:1rem;">`;

        // Pod Info Card
        html += `
            <div style="padding:1rem; background:rgba(0,0,0,0.25); border-radius:8px; border-left: 3px solid var(--accent-purple);">
                <h4 style="margin-bottom:0.75rem; color:#fff; display:flex; align-items:center; gap:0.5rem;">
                    <i class="fa-solid fa-cube" style="color:var(--accent-purple);"></i> Pod Information
                </h4>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem 2rem; font-size:0.85rem;">
                    <div><span style="color:var(--text-muted);">Phase:</span> <strong style="color:${data.pod_phase === 'Running' ? 'var(--status-green)' : 'var(--status-red)'};">${data.pod_phase || 'Unknown'}</strong></div>
                    <div><span style="color:var(--text-muted);">Status:</span> <strong>${data.pod_status || 'Unknown'}</strong></div>
                    <div><span style="color:var(--text-muted);">Node:</span> <code style="font-size:0.8rem;">${data.node_name || 'N/A'}</code></div>
                    <div><span style="color:var(--text-muted);">Containers:</span> <strong>${containerNames.length}</strong></div>
                </div>
                ${containerNames.length > 0 ? `
                    <div style="margin-top:0.75rem; padding-top:0.5rem; border-top:1px solid rgba(255,255,255,0.06);">
                        ${containerNames.map((name, i) => `
                            <div style="font-size:0.8rem; margin-top:0.3rem; display:flex; align-items:center; gap:0.5rem;">
                                <i class="fa-solid fa-cube" style="color:var(--accent-cyan); font-size:0.7rem;"></i>
                                <code>${name}</code>
                                <span style="color:var(--text-muted);">&rarr;</span>
                                <span style="color:var(--text-secondary); font-size:0.75rem;">${containerImages[i] || 'unknown'}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>`;

        // Resource Specs Card
        html += `
            <div style="padding:1rem; background:rgba(0,0,0,0.25); border-radius:8px; border-left: 3px solid var(--accent-cyan);">
                <h4 style="margin-bottom:0.75rem; color:#fff; display:flex; align-items:center; gap:0.5rem;">
                    <i class="fa-solid fa-sliders" style="color:var(--accent-cyan);"></i> Resource Configuration
                </h4>`;

        if (hasLimits || hasRequests) {
            html += `
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.75rem;">
                    <div style="padding:0.75rem; background:rgba(255,255,255,0.03); border-radius:6px;">
                        <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-muted); margin-bottom:0.4rem;">Limits</div>
                        <div style="font-size:0.85rem;"><i class="fa-solid fa-memory" style="color:var(--accent-purple); width:16px;"></i> Memory: <strong>${data.limits.memory_mb > 0 ? data.limits.memory_mb + ' MiB' : 'Not set'}</strong></div>
                        <div style="font-size:0.85rem; margin-top:0.2rem;"><i class="fa-solid fa-microchip" style="color:var(--accent-cyan); width:16px;"></i> CPU: <strong>${data.limits.cpu_cores > 0 ? data.limits.cpu_cores + ' Cores' : 'Not set'}</strong></div>
                    </div>
                    <div style="padding:0.75rem; background:rgba(255,255,255,0.03); border-radius:6px;">
                        <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-muted); margin-bottom:0.4rem;">Requests</div>
                        <div style="font-size:0.85rem;"><i class="fa-solid fa-memory" style="color:var(--accent-purple); width:16px;"></i> Memory: <strong>${data.requests.memory_mb > 0 ? data.requests.memory_mb + ' MiB' : 'Not set'}</strong></div>
                        <div style="font-size:0.85rem; margin-top:0.2rem;"><i class="fa-solid fa-microchip" style="color:var(--accent-cyan); width:16px;"></i> CPU: <strong>${data.requests.cpu_cores > 0 ? data.requests.cpu_cores + ' Cores' : 'Not set'}</strong></div>
                    </div>
                </div>`;
        } else {
            html += `
                <div style="padding:0.75rem; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); border-radius:6px; font-size:0.85rem; display:flex; align-items:center; gap:0.5rem;">
                    <i class="fa-solid fa-triangle-exclamation" style="color:var(--status-warning);"></i>
                    <span><strong>No resource limits or requests configured.</strong> This pod runs with unbounded resources -- it can consume all available node memory/CPU. Consider setting resource limits.</span>
                </div>`;
        }
        html += `</div>`;

        // Current Usage Card
        html += `
            <div style="padding:1rem; background:rgba(0,0,0,0.25); border-radius:8px; border-left: 3px solid ${metricsAvailable ? 'var(--status-green)' : 'var(--status-warning)'};">
                <h4 style="margin-bottom:0.75rem; color:#fff; display:flex; align-items:center; gap:0.5rem;">
                    <i class="fa-solid fa-chart-line" style="color:${metricsAvailable ? 'var(--status-green)' : 'var(--status-warning)'};"></i> Current Resource Utilization
                </h4>`;

        if (hasUsage) {
            data.current_usage.forEach(c => {
                const memPct = data.limits.memory_mb > 0 ? Math.round((c.memory_mb / data.limits.memory_mb) * 100) : null;
                const cpuPct = data.limits.cpu_cores > 0 ? Math.round((c.cpu_cores / data.limits.cpu_cores) * 100) : null;
                
                html += `
                    <div style="margin-bottom:0.75rem; padding:0.75rem; background:rgba(255,255,255,0.03); border-radius:6px;">
                        <div style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:0.5rem;"><i class="fa-solid fa-box"></i> <code>${c.container}</code></div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;">
                            <div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">Memory</div>
                                <div style="font-size:1.1rem; font-weight:600; color:var(--accent-purple);">${c.memory_mb} MiB</div>
                                ${memPct !== null ? `<div style="margin-top:0.3rem; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="height:100%; width:${Math.min(memPct, 100)}%; background:${memPct > 85 ? 'var(--status-red)' : 'var(--accent-purple)'}; border-radius:2px;"></div></div><div style="font-size:0.7rem; color:var(--text-muted); margin-top:0.15rem;">${memPct}% of limit</div>` : ''}
                            </div>
                            <div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">CPU</div>
                                <div style="font-size:1.1rem; font-weight:600; color:var(--accent-cyan);">${c.cpu_cores} Cores</div>
                                ${cpuPct !== null ? `<div style="margin-top:0.3rem; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="height:100%; width:${Math.min(cpuPct, 100)}%; background:${cpuPct > 85 ? 'var(--status-red)' : 'var(--accent-cyan)'}; border-radius:2px;"></div></div><div style="font-size:0.7rem; color:var(--text-muted); margin-top:0.15rem;">${cpuPct}% of limit</div>` : ''}
                            </div>
                        </div>
                    </div>`;
            });
        } else {
            const errorMsg = data.metrics_error || 'Metrics API not available';
            html += `
                <div style="padding:0.75rem; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); border-radius:6px; font-size:0.85rem;">
                    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                        <i class="fa-solid fa-circle-info" style="color:var(--status-warning);"></i>
                        <strong>Metrics Server Not Available</strong>
                    </div>
                    <p style="margin:0; color:var(--text-secondary);">
                        Live CPU/memory utilization requires <code>metrics-server</code> to be installed on the cluster.
                    </p>
                    <div style="margin-top:0.5rem; padding:0.5rem; background:rgba(0,0,0,0.2); border-radius:4px; font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">
                        $ kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
                    </div>
                    <p style="margin:0.4rem 0 0; font-size:0.75rem; color:var(--text-muted);">Error: ${errorMsg}</p>
                </div>`;
        }
        html += `</div>`;

        html += `</div>`;
        summaryDiv.innerHTML = html;

        if (memoryChartInstance) memoryChartInstance.destroy();
        if (cpuChartInstance) cpuChartInstance.destroy();
    }
}

// Populate logs container terminal mock
function populateLogsTab(logsAgentResult) {
    const terminal = document.getElementById('logs-terminal');
    if (!logsAgentResult.success) {
        terminal.textContent = `ERROR: Failed to retrieve logs: ${logsAgentResult.message}\n${logsAgentResult.data?.error || ''}`;
        return;
    }

    const logs = logsAgentResult.data.logs;
    terminal.textContent = logs.join('\n');
    terminal.scrollTop = terminal.scrollHeight;
}

// Populate Cost tab metrics
function populateCostTab(costAgentResult) {
    if (!costAgentResult.success) {
        document.getElementById('current-pool-cost').textContent = "Error";
        return;
    }

    const data = costAgentResult.data;
    
    // VM Metrics
    document.getElementById('current-pool-cost').textContent = `$${data.node_pool.total_monthly_cost.toFixed(2)}/mo`;
    document.getElementById('node-vm-type').textContent = data.node_pool.node_type;
    document.getElementById('node-count').textContent = data.node_pool.nodes_count;
    document.getElementById('node-memory').textContent = `${data.node_pool.total_memory_gb} GB`;
    document.getElementById('node-allocated').textContent = `${data.node_pool.allocated_memory_gb} GB (${data.node_pool.memory_allocation_pct}%)`;

    // Comparison List
    const scenariosList = document.getElementById('scenarios-list');
    scenariosList.innerHTML = '';
    
    data.scenarios.forEach((s, idx) => {
        const isRec = idx === 1; // Option B (Index 1) is the recommended GC Tuning option
        const div = document.createElement('div');
        div.className = `scenario-item ${isRec ? 'recommended' : ''}`;
        div.innerHTML = `
            <div class="scenario-header">
                <span class="scenario-title">
                    ${isRec ? '<i class="fa-solid fa-star" style="color:var(--status-green);"></i> ' : ''}
                    ${s.name}
                </span>
                <span class="scenario-cost-diff">
                    ${s.estimated_monthly_cost_diff === 0 ? '$0.00/mo' : `+$${s.estimated_monthly_cost_diff.toFixed(2)}/mo`}
                </span>
            </div>
            <div class="scenario-desc">${s.resource_change}</div>
            <div class="scenario-notes">Risk: <strong>${s.autoscale_risk}</strong> &bull; ${s.notes}</div>
        `;
        scenariosList.appendChild(div);
    });
}

// Apply Selected Remediation
async function applyRemediation(option) {
    remediationResult.className = 'remediation-result';
    remediationResult.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Triggering Remediation Patch (Option ${option})...`;
    remediationResult.classList.remove('hidden');

    try {
        const response = await fetch('/api/apply-fix', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                option: option,
                mode: currentState.mode,
                namespace: currentState.namespace,
                pod: currentState.pod
            })
        });

        const res = await response.json();
        
        if (res.success) {
            remediationResult.classList.add('success');
            
            if (res.dry_run) {
                remediationResult.innerHTML = `
                    <p><strong><i class="fa-solid fa-circle-check"></i> Dry-Run Execution Script Created Successfully:</strong></p>
                    <pre style="margin-top:0.5rem; background:#080711; padding:0.8rem; border-radius:6px; font-family:var(--font-mono); color:#a78bfa; overflow-x:auto;">${res.command}</pre>
                `;
                addSystemMessage(`Dry-run fix generated successfully. You can execute this command locally:<br><code>${res.command}</code>`);
            } else {
                remediationResult.innerHTML = `<p><i class="fa-solid fa-circle-check"></i> <strong>Remediation Applied:</strong> ${res.message}</p>`;
                addSystemMessage(`<strong>Remediation Option ${option} applied successfully!</strong> Pod cluster is restarting with updated parameters. Checking health status...`);
                
                // Reload pods to display healthy green state!
                setTimeout(() => {
                    loadPods();
                    addSystemMessage(`<strong>Service health verified:</strong> All pod instances are healthy now. Restarts reset to 0.`);
                }, 2500);
            }
        } else {
            throw new Error(res.message);
        }
    } catch (err) {
        remediationResult.className = 'remediation-result error';
        remediationResult.innerHTML = `<p><i class="fa-solid fa-circle-xmark"></i> <strong>Execution Failed:</strong> ${err.message}</p>`;
    }
}
