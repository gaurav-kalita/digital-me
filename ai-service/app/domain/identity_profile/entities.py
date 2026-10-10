"""Core identity profile domain entities."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Skill:
    name: str
    category: str = ""


@dataclass(frozen=True)
class ExperienceSummary:
    company: str
    role: str
    summary: str


@dataclass(frozen=True)
class IdentityProfile:
    name: str
    summary: str
    skills: List[Skill] = field(default_factory=list)
    experiences: List[ExperienceSummary] = field(default_factory=list)
