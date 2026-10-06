import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ModelResponse(BaseModel):
    """
    Standardized response from any LLM model.
    """
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: int = 0
    tool_calls: int = 0

    # Can optionally contain the raw Pydantic parsed object if output_schema was provided
    parsed_object: Optional[Any] = None


class ModelAdapter(ABC):
    """
    Abstract base class for all LLM providers to ensure
    vendor lock-in avoidance and unified logging/cost tracking.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[type[BaseModel]] = None
    ) -> ModelResponse:
        """
        Generates a response from the LLM. If response_schema is provided,
        it should force the LLM to output structured JSON matching the schema.
        """
        pass

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost based on token usage.
        Should be overridden by specific provider implementations.
        """
        return 0.0


class MockAdapter(ModelAdapter):
    """
    Mock adapter for testing purposes and fast development without incurring API costs.
    """
    def __init__(self, model_name: str = "mock-model-fast"):
        super().__init__(model_name)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[type[BaseModel]] = None
    ) -> ModelResponse:
        start_time = time.time()

        # Simulate processing time
        time.sleep(0.1)

        latency_ms = int((time.time() - start_time) * 1000)
        input_tokens = len(user_prompt.split()) + len(system_prompt.split())
        output_tokens = 50
        cost = self._calculate_cost(input_tokens, output_tokens)

        parsed = None
        content = "Mock response content."

        if response_schema:
            # For testing, we try to create an empty/dummy instance of the schema
            # This is highly naive and just for the Mock Adapter.
            try:
                # We assume the schema can be instantiated with default or missing (which might fail)
                # In a real mock we would construct a valid dict, here we just return string if we can't.
                content = "{}"
            except Exception:
                pass

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            latency_ms=latency_ms,
            tool_calls=0,
            parsed_object=parsed
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Dummy cost calculation: $0.01 per 1k input, $0.03 per 1k output
        return (input_tokens / 1000 * 0.01) + (output_tokens / 1000 * 0.03)
