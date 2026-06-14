<p align="center">
  <h1 align="center">🚨 Kubernetes Incident Commander Agent</h1>
  <p align="center">
    An interactive, multi-agent platform engineering dashboard that automates root cause analysis (RCA) and cost-aware remediations for unhealthy Kubernetes workloads.
    <br />
    Powered by <strong>Gemini API Reasoning</strong> and <strong>Parallel Subagent Orchestration</strong>.
  </p>
</p>

<p align="center">
  <a href="#-key-features">Features</a> •
  <a href="#-demo">Demo</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-contributing">Contributing</a> •
  <a href="#-license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+"/>
  <img src="https://img.shields.io/badge/Flask-3.0+-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/Kubernetes-ready-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white" alt="Kubernetes"/>
  <img src="https://img.shields.io/badge/Gemini_AI-powered-8E75B2?style=for-the-badge&logo=google&logoColor=white" alt="Gemini AI"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
</p>

---

## 📸 Demo

<!-- Add your screenshots/GIFs here -->
<!-- ![Dashboard Screenshot](docs/screenshots/dashboard.png) -->
<!-- ![Agent Execution](docs/screenshots/agent-execution.gif) -->

> **💡 Tip:** Run the app in **Demo Cluster** mode to experience a fully simulated OOMKilled production incident — no live cluster required!

---

## 🚀 Key Features

| Feature | Description |
|---------|-------------|
| **🤖 Multi-Agent Coordination** | Spawns four specialized subagents that query logs, metrics, events, and cloud costs in parallel |
| **🧠 Gemini Reasoning** | Correlates raw cluster diagnostics into a unified RCA report with actionable recommendations |
| **💰 Cost Analysis** | Computes node allocation, headroom, and evaluates the financial impact of remediation options |
| **🎭 Simulated Demo Mode** | High-fidelity replica of an OOMKilled production outage with interactive UI state changes |
| **🔴 Live Cluster Mode** | Uses local `kubectl` to run real diagnoses on live workloads in the active namespace |
| **✨ Premium Dashboard** | Dark glassmorphism theme, Chart.js telemetry, real-time agent animations, and interactive console |

---

## 🚦 Getting Started

### Prerequisites

- Python 3.9+
- (Optional) `kubectl` configured with a cluster context for live mode
- (Optional) A [Gemini API key](https://aistudio.google.com/apikey) — the app falls back to rule-based analysis if no key is provided

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/k8s-incident-commander-agent.git
cd k8s-incident-commander-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Gemini API key (optional)
# GOOGLE_API_KEY=your_key_here
```

### Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. If port 5000 is in use (common on macOS due to AirPlay Receiver):

```bash
PORT=5001 python app.py
```

---

## 🔬 Interactive Scenario Walkthrough

1. **Spot the Outage** — In **Demo Cluster** mode, pod `payment-processor-78cf4d89-x9w2` appears in red `CrashLoopBackOff` with 14 restarts.
2. **Ask the Commander** — Click the quick suggestion: *"Why are my pods restarting in production?"*
3. **Watch Agents Execute** — The Multi-Agent Orchestrator panel animates in real-time as Logs, Metrics, Events, and Cost agents work in parallel.
4. **Explore the Diagnostics**:
   - **RCA Report** — Compiled root cause summary and recommendations
   - **Telemetry** — Chart.js graph showing memory spiking to 99.6% of 512MiB limit before the crash
   - **Container Logs** — JVM stack trace with `java.lang.OutOfMemoryError`
   - **Cost Impact** — Side-by-side comparison: GC tuning (Option B) avoids node autoscale, saving **$140/month**
5. **Apply Remediation** — Click **"Apply GC Tuning Patch"** in the RCA report tab.
6. **Verify Resolution** — Pod status turns green `Running`, restarts reset to `0`, and memory usage drops.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, Flask |
| **Agent Framework** | Custom parallel multi-threading orchestrator |
| **Kubernetes** | `kubectl` subprocess interface |
| **Frontend** | HTML5, CSS3 (glassmorphism), Vanilla JS |
| **Charts** | Chart.js |
| **Icons** | FontAwesome |
| **Markdown** | markdown-it |
| **AI Engine** | Gemini SDK (with rule-based fallback) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Backend (app.py)                │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │            Incident Commander Orchestrator         │  │
│  │                                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────┐  │  │
│  │  │   Logs   │ │ Metrics  │ │  Events  │ │Cost │  │  │
│  │  │  Agent   │ │  Agent   │ │  Agent   │ │Agent│  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬──┘  │  │
│  │       │             │            │           │     │  │
│  │       └─────────────┴────────────┴───────────┘     │  │
│  │                      │                             │  │
│  │              ┌───────▼────────┐                    │  │
│  │              │  Gemini Client │                    │  │
│  │              │  (LLM / RCA)  │                    │  │
│  │              └────────────────┘                    │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│  ┌──────────────────────▼────────────────────────────┐  │
│  │   kubectl  /  Demo Data Simulator                 │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Dashboard (HTML/JS) │
│  Glassmorphism UI    │
│  Chart.js Telemetry  │
└─────────────────────┘
```

---

## 📦 Project Structure

```
.
├── app.py                 # Main Flask backend server
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── agents/                # Multi-agent package
│   ├── __init__.py        # Package exports
│   ├── base.py            # Core agent interfaces
│   ├── logs_agent.py      # Subagent: Container logs
│   ├── metrics_agent.py   # Subagent: CPU & Memory telemetry
│   ├── events_agent.py    # Subagent: Lifecycle & K8s events
│   ├── cost_agent.py      # Subagent: Node pool cost estimator
│   ├── gemini_client.py   # Gemini LLM and fallback report engine
│   └── orchestrator.py    # Parallel execution orchestrator
├── templates/
│   └── index.html         # Dashboard view
└── static/
    ├── app.js             # Frontend logic & charts
    └── style.css          # Styling & animations
```

---

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) for details on how to set up the project for development and submit pull requests.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ for the Kubernetes community
</p>
