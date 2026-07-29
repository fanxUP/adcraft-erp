"""Validated contract between backend AI actions and frontend page controls."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from urllib.parse import urlsplit

from app.core import permissions


@dataclass(frozen=True)
class PageCapabilityRoute:
    name: str
    path: str
    marker_files: tuple[str, ...]
    required_permission: str

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
    purpose: str
    prerequisites: tuple[str, ...]
    completion_signal: str
    blocking_conditions: tuple[str, ...]
    effect: str
    requires_confirmation: bool


@dataclass(frozen=True)
class PageContract:
    page_key: str
    route_name: str
    path: str
    title: str
    purpose: str
    workflow_stage: str
    business_types: frozenset[str]


@lru_cache(maxsize=1)
def _load_contract_data() -> dict:
    contract_file = resources.files("app.ai_assistant.contracts").joinpath(
        "page_capabilities.json"
    )
    return json.loads(contract_file.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_page_capabilities() -> tuple[PageCapability, ...]:
    """Load the source-controlled frontend capability contract."""
    data = _load_contract_data()
    semantics = data.get("semantics", {})
    capabilities = tuple(
        PageCapability(
            target_key=item["target_key"],
            business_types=frozenset(item["business_types"]),
            routes=tuple(
                PageCapabilityRoute(
                    name=route["name"],
                    path=route["path"],
                    marker_files=tuple(route["marker_files"]),
                    required_permission=semantics[item["target_key"]][
                        "required_permissions"
                    ][route["name"]],
                )
                for route in item["routes"]
            ),
            purpose=semantics[item["target_key"]]["purpose"],
            prerequisites=tuple(
                semantics[item["target_key"]]["prerequisites"]
            ),
            completion_signal=semantics[item["target_key"]]["completion_signal"],
            blocking_conditions=tuple(
                semantics[item["target_key"]]["blocking_conditions"]
            ),
            effect=semantics[item["target_key"]]["effect"],
            requires_confirmation=semantics[item["target_key"]][
                "requires_confirmation"
            ],
        )
        for item in data["capabilities"]
    )
    keys = [capability.target_key for capability in capabilities]
    if len(keys) != len(set(keys)):
        raise RuntimeError("AI 页面能力契约存在重复 target_key")
    if set(keys) != set(semantics):
        raise RuntimeError("AI 页面能力契约的控件与语义登记不一致")
    permission_codes = _registered_permission_codes()
    for capability in capabilities:
        if capability.effect not in {"read", "write"}:
            raise RuntimeError(
                f"AI 页面能力契约操作类型无效：{capability.target_key}"
            )
        if capability.effect == "write" and not capability.requires_confirmation:
            raise RuntimeError(
                f"AI 写操作未要求人工确认：{capability.target_key}"
            )
        if not all(
            (
                capability.purpose,
                capability.prerequisites,
                capability.completion_signal,
                capability.blocking_conditions,
            )
        ):
            raise RuntimeError(
                f"AI 页面能力契约语义不完整：{capability.target_key}"
            )
        for route in capability.routes:
            if route.required_permission not in permission_codes:
                raise RuntimeError(
                    "AI 页面能力契约使用了未登记权限："
                    f"{capability.target_key} -> {route.required_permission}"
                )
    return capabilities


GUIDANCE_BUSINESS_TYPES = frozenset(
    _load_contract_data()["guidance_business_types"]
)


@lru_cache(maxsize=1)
def load_page_contracts() -> tuple[PageContract, ...]:
    """Load the canonical purpose and workflow stage for guided pages."""
    pages = tuple(
        PageContract(
            page_key=item["page_key"],
            route_name=item["route_name"],
            path=item["path"],
            title=item["title"],
            purpose=item["purpose"],
            workflow_stage=item["workflow_stage"],
            business_types=frozenset(item["business_types"]),
        )
        for item in _load_contract_data()["pages"]
    )
    keys = [page.page_key for page in pages]
    if len(keys) != len(set(keys)):
        raise RuntimeError("AI 页面能力契约存在重复 page_key")
    return pages


def page_capability_contract_payload() -> dict:
    """Return an isolated payload suitable for AI rule hashing and persistence."""
    data = _load_contract_data()
    return {
        "version": data["version"],
        "guidance_business_types": deepcopy(data["guidance_business_types"]),
        "pages": deepcopy(data["pages"]),
        "target_keys": [
            item["target_key"]
            for item in data["capabilities"]
        ],
        "capabilities": deepcopy(data["capabilities"]),
        "semantics": deepcopy(data["semantics"]),
    }


def _registered_permission_codes() -> frozenset[str]:
    return frozenset(
        value
        for name, value in vars(permissions).items()
        if name.startswith("PERM_") and isinstance(value, str)
    )


def _resolve_page_action(
    target_key: str,
    target_path: str,
) -> tuple[PageCapability, PageCapabilityRoute]:
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
    route = next(
        (item for item in capability.routes if item.matches(target_path)),
        None,
    )
    if route is None:
        raise ValueError(
            f"AI 页面控件与目标路径不匹配：{target_key} -> {target_path}"
        )
    return capability, route


def build_page_action_semantics(target_key: str, target_path: str) -> dict:
    """Return trusted operation guidance for one registered page control."""
    capability, route = _resolve_page_action(target_key, target_path)
    return {
        "purpose": capability.purpose,
        "prerequisites": list(capability.prerequisites),
        "completion_signal": capability.completion_signal,
        "blocking_conditions": list(capability.blocking_conditions),
        "effect": capability.effect,
        "requires_confirmation": capability.requires_confirmation,
        "required_permission": route.required_permission,
    }


def validate_page_action_target(target_key: str, target_path: str) -> None:
    """Fail closed when AI guidance points to an undeclared or wrong page control."""
    _resolve_page_action(target_key, target_path)


def page_capability_health() -> dict:
    """Summarize contract completeness for CI and the admin health page."""
    capabilities = load_page_capabilities()
    known_permissions = _registered_permission_codes()
    used_permissions = {
        route.required_permission
        for capability in capabilities
        for route in capability.routes
    }
    write_capabilities = [
        capability
        for capability in capabilities
        if capability.effect == "write"
    ]
    return {
        "version": _load_contract_data()["version"],
        "page_count": len(load_page_contracts()),
        "capability_count": len(capabilities),
        "semantic_complete_count": sum(
            bool(
                capability.purpose
                and capability.prerequisites
                and capability.completion_signal
                and capability.blocking_conditions
            )
            for capability in capabilities
        ),
        "write_capability_count": len(write_capabilities),
        "all_write_actions_require_confirmation": all(
            capability.requires_confirmation
            for capability in write_capabilities
        ),
        "unknown_permissions": sorted(used_permissions - known_permissions),
    }
