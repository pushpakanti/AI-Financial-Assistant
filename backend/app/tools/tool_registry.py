"""Auto-discover and execute service-backed tools for agent workflows."""

import inspect
import logging
import pkgutil
from importlib import import_module
from typing import Any

from sqlalchemy.orm import Session

from app.tools.base import BaseTool


logger = logging.getLogger(__name__)


class ToolRegistry:
    """Discover tool adapters by module convention and expose a JSON execution boundary."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._tools = self._discover_tools()

    def available_tools(self) -> list[dict[str, str]]:
        """Return agent-safe descriptions for all discovered tools."""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def execute(
        self, tool_name: str, user_id: int, action: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a discovered tool and always return a JSON-compatible envelope."""
        tool = self._tools.get(tool_name.strip().lower())
        if tool is None:
            return {
                "success": False,
                "tool": tool_name,
                "action": action,
                "error": {"code": 404, "message": "Tool not found."},
            }
        result = tool.execute(user_id, action, payload)
        if not result.get("success"):
            self._rollback_failed_tool_session()
        return result

    def _rollback_failed_tool_session(self) -> None:
        """Reset the shared request session so one failed tool cannot poison later tools."""
        if not self._db.in_transaction():
            return
        try:
            self._db.rollback()
        except Exception:  # pragma: no cover - rollback must not replace the original tool result
            logger.exception("Failed to roll back database session after tool failure")

    def _discover_tools(self) -> dict[str, BaseTool]:
        """Discover subclasses from `*_tool.py` modules without a hand-maintained list."""
        package = import_module("app.tools")
        tools: dict[str, BaseTool] = {}
        for module_info in pkgutil.iter_modules(package.__path__):
            if not module_info.name.endswith("_tool"):
                continue
            module = import_module(f"{package.__name__}.{module_info.name}")
            for _, tool_class in inspect.getmembers(module, inspect.isclass):
                if tool_class is BaseTool or not issubclass(tool_class, BaseTool):
                    continue
                tool = tool_class(self._db)
                if tool.name in tools:
                    raise RuntimeError(f"Duplicate tool name discovered: {tool.name}")
                tools[tool.name] = tool
                logger.debug("Discovered AI tool name=%s module=%s", tool.name, module_info.name)
        return tools
