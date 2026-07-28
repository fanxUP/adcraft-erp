"""Tool registrations for AI Assistant."""

def register_all_tools():
    from app.ai_assistant.tools.customer_tools import register_customer_tools
    from app.ai_assistant.tools.order_tools import register_order_tools
    from app.ai_assistant.tools.finance_tools import register_finance_tools
    from app.ai_assistant.tools.task_tools import register_task_tools
    from app.ai_assistant.tools.installation_tools import register_installation_tools
    from app.ai_assistant.tools.quote_tools import register_quote_tools
    from app.ai_assistant.tools.workflow_tools import register_workflow_tools
    from app.ai_assistant.tools.status_action_tools import register_status_action_tools
    register_customer_tools()
    register_order_tools()
    register_finance_tools()
    register_task_tools()
    register_installation_tools()
    register_quote_tools()
    register_workflow_tools()
    register_status_action_tools()
