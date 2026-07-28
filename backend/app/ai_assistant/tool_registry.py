"""Tool registry — register and look up AI tools."""

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class AiToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    risk_level: str = "level_1"
    required_permission: str = ""
    requires_confirmation: bool = False
    handler: Callable[..., Coroutine[Any, Any, dict]] | None = None


class ToolRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: AiToolDefinition):
        self._tools[tool.name] = tool

    def get(self, name: str) -> AiToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[AiToolDefinition]:
        return list(self._tools.values())

    def to_openai_format(self) -> list[dict]:
        return [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self._tools.values()
        ]

    def to_prompt_format(self) -> list[dict]:
        return [
            {
                "name": t.name, "description": t.description, "parameters": t.parameters,
                "risk_level": t.risk_level, "required_permission": t.required_permission,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in self._tools.values()
        ]
