import time
from concurrent.futures import ThreadPoolExecutor
from agents.logs_agent import LogsAgent
from agents.metrics_agent import MetricsAgent
from agents.events_agent import EventsAgent
from agents.cost_agent import CostAgent
from agents.gemini_client import GeminiClient

class IncidentCommanderOrchestrator:
    def __init__(self):
        self.logs_agent = LogsAgent()
        self.metrics_agent = MetricsAgent()
        self.events_agent = EventsAgent()
        self.cost_agent = CostAgent()
        self.gemini_client = GeminiClient()

    def run_investigation(self, query, context=None):
        """
        Runs the multi-agent investigation.
        :param query: The user query, e.g. "Why are my pods restarting in production?"
        :param context: Dict including mode (demo or live), namespace, pod, etc.
        :return: Dict with orchestration details, subagent results, and final RCA.
        """
        if context is None:
            context = {"mode": "demo", "namespace": "production", "pod": "payment-processor-78cf4d89-x9w2"}

        start_time = time.time()
        print(f"[Orchestrator] Starting incident investigation: '{query}'")
        print(f"[Orchestrator] Context: {context}")

        # Execute subagents in parallel using a ThreadPoolExecutor
        results = {}
        agents = {
            "logs_agent": self.logs_agent,
            "metrics_agent": self.metrics_agent,
            "events_agent": self.events_agent,
            "cost_agent": self.cost_agent
        }

        def run_agent_task(name, agent):
            agent_start = time.time()
            try:
                res = agent.run(context)
                duration = time.time() - agent_start
                res_dict = res.to_dict()
                res_dict["duration_seconds"] = round(duration, 3)
                return name, res_dict
            except Exception as e:
                duration = time.time() - agent_start
                return name, {
                    "agent_name": agent.name,
                    "success": False,
                    "data": {"error": str(e)},
                    "message": f"Execution failed: {str(e)}",
                    "timestamp": time.time(),
                    "duration_seconds": round(duration, 3)
                }

        print("[Orchestrator] Spawning subagents in parallel...")
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Map agent executions
            futures = [executor.submit(run_agent_task, name, agent) for name, agent in agents.items()]
            for future in futures:
                name, result = future.result()
                results[name] = result
                print(f"[Orchestrator] Subagent '{result['agent_name']}' finished in {result['duration_seconds']}s. Status: {'Success' if result['success'] else 'Failed'}")

        # Correlate findings using Gemini (or fallback engine)
        print("[Orchestrator] Correlating subagent outputs and invoking Gemini reasoning...")
        rca_report = self.gemini_client.analyze_incident(
            query=query,
            logs=results["logs_agent"],
            metrics=results["metrics_agent"],
            events=results["events_agent"],
            cost=results["cost_agent"],
            context=context
        )

        total_duration = time.time() - start_time
        print(f"[Orchestrator] Investigation completed in {round(total_duration, 3)} seconds.")

        return {
            "query": query,
            "context": context,
            "subagent_results": results,
            "rca_report": rca_report,
            "total_duration_seconds": round(total_duration, 3),
            "timestamp": time.time()
        }
