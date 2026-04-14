from pydantic import BaseModel
from typing import Any, Dict, Optional


class RetrievalCandidate(BaseModel):
    document: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None