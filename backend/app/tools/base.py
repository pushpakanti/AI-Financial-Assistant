"""Common JSON contract for service-backed AI tools."""

from abc import ABC, abstractmethod
import logging
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.core.exceptions import AppException


logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """A user-scoped tool whose public execution result is always JSON-compatible."""

    name: str
    description: str

    @abstractmethod
    def _execute(self, user_id: int, action: str, payload: dict[str, Any]) -> Any:
        """Perform a domain operation using services; never access SQL from agents."""

    def execute(self, user_id: int, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a tool operation and normalize all expected outcomes into JSON."""
        try:
            data = self._execute(user_id, action, payload or {})
            return {"success": True, "tool": self.name, "action": action, "data": jsonable_encoder(data)}
        except AppException as error:
            return {
                "success": False,
                "tool": self.name,
                "action": action,
                "error": {"code": error.status_code, "message": error.message},
            }
        except (ValidationError, ValueError, KeyError) as error:
            return {
                "success": False,
                "tool": self.name,
                "action": action,
                "error": {"code": 422, "message": str(error)},
            }
        except Exception as error:  # pragma: no cover - final tool boundary protection
            logger.exception("Unexpected tool failure tool=%s action=%s", self.name, action)
            return {
                "success": False,
                "tool": self.name,
                "action": action,
                "error": {
                    "code": 500,
                    "type": error.__class__.__name__,
                    "message": str(error),
                },
            }

    @staticmethod
    def _id(payload: dict[str, Any], field: str = "id") -> int:
        value = payload[field]
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{field} must be a positive integer.")
        return value
