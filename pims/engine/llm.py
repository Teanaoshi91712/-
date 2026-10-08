import time
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

import openai

from pims.config import settings

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


class OpenAIAdapter(ModelAdapter):
    """
    Actual implementation for OpenAI API. Uses `response_format` to enforce
    strict JSON schema parsing via Pydantic when provided.
    """
    def __init__(self, model_name: str = settings.DEFAULT_OPENAI_MODEL):
        super().__init__(model_name)
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in the environment or .env file.")
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[type[BaseModel]] = None
    ) -> ModelResponse:

        start_time = time.time()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        parsed_obj = None
        raw_content = ""

        # Determine whether to use standard completion or the parsed structured output
        if response_schema:
            try:
                # Use beta parsed feature for structured output
                completion = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    response_format=response_schema
                )
                parsed_obj = completion.choices[0].message.parsed
                # We also attempt to extract the raw string representation for the Audit Log
                raw_content = completion.choices[0].message.content or "{}"
            except Exception as e:
                # Fallback to standard chat completions if parse fails or is unsupported
                # This ensures the application doesn't crash completely
                raw_content = f'{{"error": "Failed to parse structured output", "details": "{str(e)}"}}'
                completion = None
        else:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            raw_content = completion.choices[0].message.content

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract usage metrics if completion was successful
        input_tokens = 0
        output_tokens = 0
        if completion and hasattr(completion, 'usage') and completion.usage:
            input_tokens = completion.usage.prompt_tokens
            output_tokens = completion.usage.completion_tokens

        cost = self._calculate_cost(input_tokens, output_tokens)

        return ModelResponse(
            content=raw_content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            latency_ms=latency_ms,
            tool_calls=0, # Assuming no tools used for now, just schema parsing
            parsed_object=parsed_obj
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Cost mapping based on model. Note: These are example estimates.
        if "gpt-4o-mini" in self.model_name:
            return (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
        elif "gpt-4o" in self.model_name:
            return (input_tokens / 1_000_000 * 5.00) + (output_tokens / 1_000_000 * 15.00)
        return 0.0


def get_llm_adapter(model_name: Optional[str] = None) -> ModelAdapter:
    """
    Factory function to get the appropriate LLM adapter based on application configuration.
    """
    if settings.USE_MOCK_LLM:
        return MockAdapter(model_name=model_name or "mock-model-fast")
    else:
        return OpenAIAdapter(model_name=model_name or settings.DEFAULT_OPENAI_MODEL)
