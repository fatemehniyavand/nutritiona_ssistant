from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MemoryEntry:
    question: str
    answer: str
    mode: str
    confidence: str
    sources_used: List[str] = field(default_factory=list)


@dataclass
class MemoryMatchResult:
    found: bool
    matched_entry: Optional[MemoryEntry] = None
    similarity_score: float = 0.0