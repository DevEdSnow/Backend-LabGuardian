"""
Common API dependencies for LabGuardian AI.

This module contains reusable dependencies that can be
injected into FastAPI routes.
"""

from typing import Generator

def get_current_user():
"""
Placeholder for the authenticated user dependency.

```
Authentication will be implemented later.
"""
return None
```

def get_request_context() -> dict:
"""
Returns common request context.

```
This can later include information such as:
- current user
- laboratory
- permissions
- request metadata
"""
return {
    "service": "LabGuardian AI",
}
```
