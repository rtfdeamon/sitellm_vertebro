"""Admin authentication and identity management."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AdminIdentity:
    """Represents authenticated admin context."""

    username: str
    is_super: bool
    projects: tuple[str, ...] = ()

    def can_access_project(self, project: str | None) -> bool:
        if self.is_super:
            return True
        if not project:
            return False
        normalized = project.strip().lower()
        return normalized in self.projects

    @property
    def primary_project(self) -> str | None:
        return self.projects[0] if self.projects else None
