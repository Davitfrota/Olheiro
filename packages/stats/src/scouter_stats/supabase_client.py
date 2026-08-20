"""Shared Supabase client for scouter-stats CLIs."""

from __future__ import annotations

import os
from pathlib import Path


def load_env() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise SystemExit(f"Missing env var: {key}")
    return val


SERVICE_ROLE_HINT = (
    "SUPABASE_SERVICE_ROLE_KEY required (anon write policies revoked). "
    "Dashboard → Project Settings → API Keys → service_role: "
    "https://supabase.com/dashboard/project/ggeyvjhvdvxbxjdrexoa/settings/api-keys"
)


def get_supabase(*, require_service_role: bool = True):
    from supabase import create_client

    load_env()
    url = env("SUPABASE_URL")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if require_service_role:
        if not service:
            raise SystemExit(SERVICE_ROLE_HINT)
        return create_client(url, service)
    key = service or env("SUPABASE_ANON_KEY")
    return create_client(url, key)
