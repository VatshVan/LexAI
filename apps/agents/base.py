from abc import ABC, abstractmethod
from time import perf_counter
import structlog
from pydantic import BaseModel

log = structlog.get_logger()


class AgentExecutionError(Exception):
    def __init__(self, agent: str, cause: Exception):
        self.agent = agent
        self.cause = cause
        super().__init__(f"Agent '{agent}' failed: {cause}")


class BaseAgent(ABC):
    agent_name: str = "BaseAgent"

    def execute(self, *args, **kwargs):
        start = perf_counter()
        bound = log.bind(agent=self.agent_name)
        bound.info("agent_start")
        try:
            result = self._execute(*args, **kwargs)
            bound.info("agent_complete",
                       duration_ms=int((perf_counter() - start) * 1000))
            return result
        except AgentExecutionError:
            raise
        except Exception as e:
            bound.error("agent_failed", error=str(e))
            raise AgentExecutionError(self.agent_name, e)

    @abstractmethod
    def _execute(self, *args, **kwargs):
        ...
