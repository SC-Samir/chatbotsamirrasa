from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class ParseRequest(BaseModel):
    text: str


class ParseResponse(BaseModel):
    intent: Dict[str, Any]
    entities: List[Dict[str, Any]]
    text: str
