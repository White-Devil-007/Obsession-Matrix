from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TaskModel:
    id: int
    interest_id: int
    title: str
    description: str = ""
    status: str = "not_started"  # not_started, in_progress, done
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "interest_id": self.interest_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class InterestModel:
    id: int
    name: str
    parent_id: Optional[int] = None
    is_current_obsession: bool = False
    custom_progress: str = "Not Started"
    status: str = "active"  # active, archived
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    accessed_at: Optional[str] = None
    path: str = ""  # e.g., "Cybersecurity -> Web Security -> XSS"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "is_current_obsession": self.is_current_obsession,
            "custom_progress": self.custom_progress,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "accessed_at": self.accessed_at,
            "path": self.path or self.name,
        }

@dataclass
class InterestTreeNode:
    interest: InterestModel
    children: List["InterestTreeNode"] = field(default_factory=list)
    task_counts: dict = field(default_factory=lambda: {"total": 0, "not_started": 0, "in_progress": 0, "done": 0})

    def to_dict(self) -> dict:
        return {
            "interest": self.interest.to_dict(),
            "children": [child.to_dict() for child in self.children],
            "task_counts": self.task_counts,
        }
