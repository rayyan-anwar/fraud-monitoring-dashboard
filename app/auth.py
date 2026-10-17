"""API-key authentication with roles (viewer < analyst < admin). Framework-independent.

MONITOR_API_KEYS="alice:KEY1:analyst,bob:KEY2:admin". Empty value disables auth (local demo only: everyone is 'local-user', admin).

Author: Rayyan Anwar
"""
from __future__ import annotations

import hmac
from dataclasses import dataclass

ROLES = {"viewer": 1, "analyst": 2, "admin": 3}


class AuthError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


@dataclass(frozen=True)
class Identity:
    name: str
    role: str


def parse_keys(raw: str) -> dict[str, Identity]:
    out: dict[str, Identity] = {}
    for item in [p.strip() for p in raw.split(",") if p.strip()]:
        parts = item.split(":")
        if len(parts) != 3 or not all(parts) or parts[2] not in ROLES:
            raise ValueError("MONITOR_API_KEYS entries must look like name:key:role (role: viewer, analyst, admin)")
        if parts[1] in out:
            raise ValueError("duplicate API key in MONITOR_API_KEYS")
        out[parts[1]] = Identity(parts[0], parts[2])
    return out


class Authenticator:
    def __init__(self, keys: dict[str, Identity]):
        self.keys = keys

    @property
    def enabled(self) -> bool:
        return bool(self.keys)

    def identify(self, presented: str | None) -> Identity:
        if not self.keys:
            return Identity("local-user", "admin")
        if presented:
            for key, ident in self.keys.items():
                if hmac.compare_digest(presented.encode(), key.encode()):
                    return ident
        raise AuthError(401, "missing or invalid API key")

    def require(self, presented: str | None, role: str) -> Identity:
        ident = self.identify(presented)
        if ROLES[ident.role] < ROLES[role]:
            raise AuthError(403, f"requires role '{role}' or higher")
        return ident
