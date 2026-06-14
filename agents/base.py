import time

class AgentResult:
    def __init__(self, agent_name, success, data, message=""):
        self.agent_name = agent_name
        self.success = success
        self.data = data
        self.message = message
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp
        }

class BaseAgent:
    def __init__(self, name):
        self.name = name

    def log(self, message):
        print(f"[{self.name}] {message}")

    def run(self, context):
        """
        Executes the subagent.
        :param context: A dictionary containing query info, like namespace, pod, mode (demo vs live).
        :return: AgentResult
        """
        raise NotImplementedError("Subagents must implement the run method")
