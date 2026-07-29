"""AI Orchestrator — main loop for parsing intent, calling tools, and generating responses."""

import json
import logging
import re
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.ai_assistant.config import settings
from app.ai_assistant.llm_client import LlmClient
from app.ai_assistant.prompt_builder import PromptBuilder
from app.ai_assistant.memory_service import MemoryService
from app.ai_assistant.tool_executor import ToolExecutor
from app.ai_assistant.tool_registry import ToolRegistry
from app.ai_assistant.business_rules.catalog import (
    build_business_rule_catalog,
    render_business_rules_context,
)
from app.ai_assistant.business_rules.service import BusinessRuleSyncService


logger = logging.getLogger(__name__)


class AiOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = LlmClient(db)
        self.prompt_builder = PromptBuilder()
        self.memory_service = MemoryService(db)
        self.tool_executor = ToolExecutor(db)
        self.business_rule_service = BusinessRuleSyncService(db)

    async def process_message(self, user, message, session_id=None, context=None,
                              ip_address=None, user_agent=None):
        session = await self._get_or_create_session(user, session_id, context)
        user_msg = await self.memory_service.add_message(
            session.id, "user", message, user_id=user.id,
            metadata_json={"context": context} if context else None)

        # Multi-step tool loop: LLM → tool → result → LLM → ... → final answer
        reply_text, tool_results, pending_action = await self._tool_loop(
            user, session, message, context, user_msg.id)

        assistant_msg = await self.memory_service.add_message(
            session.id, "assistant", reply_text)

        await self._auto_title(session, message)

        return {
            "session_id": str(session.id),
            "message_id": str(assistant_msg.id),
            "reply": reply_text,
            "tool_calls": tool_results,
            "pending_action": pending_action,
        }

    async def stream_process_message(self, user, message, session_id=None, context=None,
                                      ip_address=None, user_agent=None):
        session = await self._get_or_create_session(user, session_id, context)
        yield {"type": "session", "session_id": str(session.id)}

        user_msg = await self.memory_service.add_message(
            session.id, "user", message, user_id=user.id,
            metadata_json={"context": context} if context else None)

        # Multi-step tool loop
        reply_text, tool_results, pending_action = await self._tool_loop(
            user, session, message, context, user_msg.id)

        # Stream the final reply text as one chunk (faster than 5-char chunks)
        if reply_text:
            yield {"type": "token", "text": reply_text}

        assistant_msg = await self.memory_service.add_message(
            session.id, "assistant", reply_text)

        await self._auto_title(session, message)

        if tool_results:
            yield {"type": "tool_calls", "tool_calls": tool_results}
        if pending_action:
            yield {"type": "pending_action", "pending_action": pending_action}

        yield {
            "type": "done",
            "session_id": str(session.id),
            "message_id": str(assistant_msg.id),
        }

    async def _tool_loop(self, user, session, message, context, user_msg_id,
                         max_rounds=5):
        """Multi-step loop: LLM → parse tool calls → execute → repeat until done."""
        all_tool_results = []
        final_pending_action = None
        accumulated_text = ""
        current_message = message
        round_count = 0
        page_key = context.get("page") if isinstance(context, dict) else None
        business_type = (
            context.get("business_type") if isinstance(context, dict) else None
        )
        try:
            business_rules_context = (
                await self.business_rule_service.get_prompt_context(
                    page_key=page_key,
                    business_type=business_type,
                )
            )
        except Exception:
            # AI failures must not affect ERP. Current source rules are safer
            # than a stale or unavailable database snapshot.
            logger.exception(
                "Failed to load published AI business rules; using source catalog"
            )
            business_rules_context = render_business_rules_context(
                build_business_rule_catalog(),
                page_key=page_key,
                business_type=business_type,
            )

        while round_count < max_rounds:
            round_count += 1
            history = await self.memory_service.get_history_messages(session.id)
            registry = ToolRegistry()
            tool_defs = registry.to_prompt_format()
            system_prompt = self.prompt_builder.build_system_prompt(
                user,
                context,
                tool_defs,
                business_rules_context=business_rules_context,
            )
            full_prompt = self._build_llm_prompt(history, current_message)

            try:
                llm_response = await self.llm_client.chat_completion(
                    prompt=full_prompt, system_prompt=system_prompt,
                    temperature=settings.AI_DEFAULT_TEMPERATURE)
            except Exception as e:
                if round_count == 1:
                    raise
                break

            reply_text, tool_call_blocks = self._parse_tool_calls(llm_response)
            accumulated_text += reply_text

            if not tool_call_blocks:
                break

            # Execute all tool calls in the block
            for tc in tool_call_blocks:
                tool_name = tc.get("tool") or tc.get("name", "")
                tool_args = tc.get("args") or tc.get("arguments", {})
                result = await self.tool_executor.execute_tool(
                    tool_name=tool_name, args=tool_args, user=user,
                    session_id=session.id, message_id=user_msg_id)
                result["tool_name"] = tool_name
                all_tool_results.append(result)

                if result.get("status") == "waiting_confirmation":
                    final_pending_action = {
                        "id": result["pending_action_id"],
                        "tool_name": tool_name,
                        "preview_data": result.get("preview_data", {}),
                    }

                if result.get("error_message"):
                    current_message = f"工具 {tool_name} 执行失败：{result['error_message']}"
                else:
                    # Feed tool result back as the "message" for next LLM round
                    tool_result_str = json.dumps(result.get("result", result), ensure_ascii=False)
                    current_message = (
                        f"工具 {tool_name} 返回结果如下，请根据结果继续操作或回复用户：\n"
                        f"{tool_result_str[:2000]}"
                    )

            # If a pending action was created (needs user confirmation), stop the loop
            if final_pending_action:
                if not accumulated_text:
                    accumulated_text = f"已生成预览，请确认后继续执行。"
                break

        return accumulated_text, all_tool_results, final_pending_action

    async def _get_or_create_session(self, user, session_id, context):
        if session_id:
            session = await self.memory_service.get_session(session_id)
            if session and session.user_id == user.id:
                if context:
                    await self.memory_service.update_session_context(session.id, context)
                return session
        return await self.memory_service.create_session(user.id, context=context)

    async def _auto_title(self, session, message):
        if not session.title or session.title == "新对话":
            messages = await self.memory_service.get_session_messages(session.id)
            if len(messages) <= 4:
                title_text = message[:50]
                if len(message) > 50:
                    title_text += "..."
                await self.memory_service.update_session_title(session.id, title_text)

    def _build_llm_prompt(self, history, current_message):
        parts = []
        if history:
            parts.append("## 对话历史")
            for h in history:
                role_label = "用户" if h["role"] == "user" else "AI助手"
                parts.append(f"{role_label}: {h['content']}")
        parts.append("## 当前任务")
        parts.append(current_message)
        return "\n\n".join(parts)

    def _parse_tool_calls(self, response):
        pattern = r'```tool_calls\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if not matches:
            pattern = r'```tool_calls\s*\n(.+?)(?:\n```|$)'
            matches = re.findall(pattern, response, re.DOTALL)

        cleaned = re.sub(r'```tool_calls.*?(?:```|$)', '', response, flags=re.DOTALL).strip()

        tool_calls = []
        for match in matches:
            text = match.strip()
            if text.endswith('\n```'):
                text = text[:-4].strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    tool_calls.extend(parsed)
                else:
                    tool_calls.append(parsed)
            except json.JSONDecodeError:
                pass
        return cleaned, tool_calls
