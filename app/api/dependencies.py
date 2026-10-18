
"""
Common API dependencies for LabGuardian AI.

Reusable dependencies injected into FastAPI routes.
"""

from typing import Any


def get_current_user() -> None:
    """Placeholder for future authentication."""
    return None


def get_request_context() -> dict[str, Any]:
    """Return common request context."""
    return {
        "service": "LabGuardian AI",
    }
