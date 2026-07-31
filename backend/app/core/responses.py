"""Standard response models shared by API infrastructure."""

from typing import Any, Generic, Literal, TypeVar

from pydantic import Field
from pydantic.generics import GenericModel


DataT = TypeVar("DataT")


class APIResponse(GenericModel, Generic[DataT]):
    """Base envelope returned by the API."""

    success: bool
    message: str
    data: DataT | dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, Any] = Field(default_factory=dict)


class SuccessResponse(APIResponse[DataT], Generic[DataT]):
    """Successful API response envelope."""

    success: Literal[True] = True


class ErrorResponse(APIResponse[dict[str, Any]]):
    """Failed API response envelope."""

    success: Literal[False] = False
