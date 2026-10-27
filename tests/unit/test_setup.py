import tomllib

from decisionguard.application.setup import codex_preview


def test_setup_only_previews_documented_toml(project):
    service, root = project
    before = (service.directory / "config.json").read_bytes()
    result = codex_preview(service, "frontend")
    settings = tomllib.loads(result["config_toml"])["mcp_servers"]["decisionguard"]
    assert settings["args"][-1] == "frontend"
    assert str(root) in settings["args"]
    assert result["preview_only"] and not result["automatic_event_polling"]
    assert (service.directory / "config.json").read_bytes() == before
