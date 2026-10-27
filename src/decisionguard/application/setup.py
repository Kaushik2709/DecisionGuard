"""Render documented configuration for review; never modify global client settings."""

import json
import sys
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any

from decisionguard.application.services import Service, envelope
from decisionguard.domain.models import Mutation


def codex_preview(service: Service, actor: str) -> dict[str, Any]:
    Mutation(actor=actor, idempotency_key="configuration-preview")
    arguments = [
        "-m",
        "decisionguard.adapters.mcp",
        "--root",
        service.config.root,
        "--actor",
        actor,
    ]
    config = (
        "[mcp_servers.decisionguard]\ncommand = "
        + json.dumps(sys.executable)
        + "\nargs = "
        + json.dumps(arguments)
        + "\n"
    )
    tomllib.loads(config)
    resource = files("decisionguard").joinpath("resources/decisionguard-workflow/SKILL.md")
    skill = (
        resource.read_text(encoding="utf-8")
        if resource.is_file()
        else (
            Path(__file__).resolve().parents[3] / "skills/decisionguard-workflow/SKILL.md"
        ).read_text(encoding="utf-8")
    )
    return envelope(
        preview_only=True,
        config_toml=config,
        actor=actor,
        coordinator_actor=actor in service.config.coordinators,
        source="https://learn.chatgpt.com/docs/extend/mcp?surface=cli",
        restart_required=True,
        automatic_event_polling=False,
        workflow_skill=skill,
        instruction="Review and merge this block into client configuration; unrelated settings are not changed.",
    )
