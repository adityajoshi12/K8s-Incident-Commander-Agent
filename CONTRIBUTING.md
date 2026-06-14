# Contributing to K8s Incident Commander Agent

Thanks for your interest in contributing! 🎉 Here's how to get started.

## Getting Started

### 1. Fork & Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/k8s-incident-commander-agent.git
cd k8s-incident-commander-agent
```

### 2. Set Up the Development Environment

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy the example env file and add your API key
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
```

### 3. Run the App

```bash
python app.py
```

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Use meaningful variable and function names.
- Add docstrings to new functions and classes.
- Keep functions focused and small.

## Submitting a Pull Request

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes and commit with clear, descriptive messages.
3. Push to your fork and open a Pull Request against `main`.
4. Describe **what** you changed and **why** in the PR description.
5. Link any related issues (e.g., `Closes #42`).

## Reporting Bugs

Found a bug? Please [open an issue](../../issues/new) and include:

- **What happened** — describe the unexpected behavior.
- **Steps to reproduce** — how can we trigger the bug?
- **Expected behavior** — what should have happened instead?
- **Environment** — OS, Python version, browser (if applicable).
- **Logs / screenshots** — paste any relevant error output.

## Questions?

Feel free to open a [Discussion](../../discussions) or reach out via Issues. We're happy to help!
