"""Validated contract between backend AI actions and frontend page controls."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PageCapabilityRoute:
    name: str
    path: str
    marker_files: tuple[str, ...]

    def matches(self, target_path: str) -> bool:
        route_pattern = re.escape(self.path)
        route_pattern = re.sub(r":[A-Za-z_][A-Za-z0-9_]*", r"[^/]+", route_pattern)
        actual_path = urlsplit(target_path).path.rstrip("/") or "/"
        expected = self.path.rstrip("/") or "/"
        if ":" not in expected:
            return actual_path == expected
        return re.fullmatch(route_pattern, actual_path) is not None


@dataclass(frozen=True)
class PageCapability:
    target_key: str
    business_types: frozenset[str]
    routes: tuple[PageCapabilityRoute, ...]


@lru_cache(maxsize=1)
def _load_contract_data() -> dict:
    contract_file = resources.files("app.ai_assistant.contracts").joinpath(
        "page_capabilities.json"
    )
    return json.loads(contract_file.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_page_capabilities() -> tuple[PageCapability, ...]:
    """Load the source-controlled frontend capability contract."""
    capabilities = tuple(
        PageCapability(
            target_key=item["target_key"],
            business_types=frozenset(item["business_types"]),
            routes=tuple(
                PageCapabilityRoute(
                    name=route["name"],
                    path=route["path"],
                    marker_files=tuple(route["marker_files"]),
                )
                for route in item["routes"]
            ),
        )
        for item in _load_contract_data()["capabilities"]
    )
    keys = [capability.target_key for capability in capabilities]
    if len(keys) != len(set(keys)):
        raise RuntimeError("AI 页面能力契约存在重复 target_key")
    return capabilities


GUIDANCE_BUSINESS_TYPES = frozenset(
    _load_contract_data()["guidance_business_types"]
)


def page_capability_contract_payload() -> dict:
    """Return an isolated payload suitable for AI rule hashing and persistence."""
    data = _load_contract_data()
    return {
        "version": data["version"],
        "guidance_business_types": deepcopy(data["guidance_business_types"]),
        "target_keys": [
            item["target_key"]
            for item in data["capabilities"]
        ],
        "capabilities": deepcopy(data["capabilities"]),
    }


def validate_page_action_target(target_key: str, target_path: str) -> None:
    """Fail closed when AI guidance points to an undeclared or wrong page control."""
    capability = next(
        (
            item
            for item in load_page_capabilities()
            if item.target_key == target_key
        ),
        None,
    )
    if capability is None:
        raise ValueError(f"AI 页面控件未登记：{target_key}")
    if not any(route.matches(target_path) for route in capability.routes):
        raise ValueError(
            f"AI 页面控件与目标路径不匹配：{target_key} -> {target_path}"
        )
