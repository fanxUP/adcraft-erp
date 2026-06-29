"""AI feature module — rule-based + optional AI-enhanced implementations.

All AI features work in rule-based mode without any external dependencies.
AI-enhanced mode is activated when AI_ENABLED=true and an AI_API_KEY is set.

Directory structure:
    core/         — FeatureResolver, AIClient
    rule_based/   — Zero-dependency implementations (always available)
    ai_enhanced/  — LLM/Vision/OCR implementations (requires httpx + API key)
    api/          — FastAPI route handlers
    schemas/      — Pydantic request/response models
"""
