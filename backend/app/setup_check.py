from __future__ import annotations

import sys
from dataclasses import asdict, dataclass

from .config import get_settings
from .llm.base import LLMError
from .llm.model_discovery import list_models, test_provider


@dataclass(frozen=True)
class SetupCheck:
    name: str
    ok: bool
    detail: str
    action: str


@dataclass(frozen=True)
class SetupStatus:
    ready: bool
    checks: list[SetupCheck]

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "checks": [asdict(check) for check in self.checks],
        }


def get_setup_status() -> SetupStatus:
    checks = [
        _python_runtime_check(),
        _context_menu_check(),
        _ollama_check(),
        _provider_check(),
        _storage_check(),
    ]
    return SetupStatus(ready=all(check.ok for check in checks), checks=checks)


def _python_runtime_check() -> SetupCheck:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return SetupCheck(
        name="Python runtime",
        ok=True,
        detail=f"Python {version}",
        action="No action needed.",
    )


def _context_menu_check() -> SetupCheck:
    if sys.platform != "win32":
        return SetupCheck(
            name="Windows context menu",
            ok=False,
            detail="Context menu registration is only checked on Windows.",
            action="Run Local Pilot on Windows or install the OS-specific integration.",
        )

    try:
        import winreg
    except ImportError:
        return SetupCheck(
            name="Windows context menu",
            ok=False,
            detail="Could not import Windows registry module.",
            action="Run on Windows with the standard Python runtime.",
        )

    paths = [
        r"Software\Classes\*\shell\LocalPilot\command",
        r"Software\Classes\Directory\shell\LocalPilot\command",
        r"Software\Classes\Directory\Background\shell\LocalPilot\command",
    ]
    missing = []
    for path in paths:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                value, _ = winreg.QueryValueEx(key, "")
                if "local_pilot_popup.py" not in value:
                    missing.append(path)
        except OSError:
            missing.append(path)

    if missing:
        return SetupCheck(
            name="Windows context menu",
            ok=False,
            detail=f"{len(missing)} registry entries missing or not pointing to Local Pilot.",
            action="Run desktop/registry/install-local-pilot-dev.ps1 or import add-local-pilot-dev.reg.",
        )

    return SetupCheck(
        name="Windows context menu",
        ok=True,
        detail="Local Pilot is registered for files, folders, and folder background.",
        action="No action needed.",
    )


def _ollama_check() -> SetupCheck:
    settings = get_settings()
    try:
        models = list_models("ollama")
    except LLMError as exc:
        return SetupCheck(
            name="Ollama",
            ok=False,
            detail=str(exc),
            action="Open Ollama, then pull a model such as gemma3:1b.",
        )

    if settings.ollama_model not in models:
        return SetupCheck(
            name="Ollama",
            ok=False,
            detail=f"Ollama is running, but {settings.ollama_model} is not installed.",
            action=f"Run: ollama pull {settings.ollama_model}",
        )

    return SetupCheck(
        name="Ollama",
        ok=True,
        detail=f"Ollama is reachable with {len(models)} installed model(s).",
        action="No action needed.",
    )


def _provider_check() -> SetupCheck:
    settings = get_settings()
    provider = settings.model_provider

    if provider == "auto":
        provider = "ollama"

    try:
        model = test_provider(provider)
    except LLMError as exc:
        return SetupCheck(
            name="Selected provider",
            ok=False,
            detail=f"{provider} is not ready: {exc}",
            action="Open Settings, choose a working provider, and click Test beside that provider.",
        )

    return SetupCheck(
        name="Selected provider",
        ok=True,
        detail=f"{provider} works. Example model: {model}",
        action="No action needed.",
    )


def _storage_check() -> SetupCheck:
    try:
        from .rag_store import DB_PATH

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        probe = DB_PATH.parent / ".setup_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return SetupCheck(
            name="Local memory storage",
            ok=False,
            detail=str(exc),
            action="Make sure backend/data is writable.",
        )

    return SetupCheck(
        name="Local memory storage",
        ok=True,
        detail="Local memory folder is writable.",
        action="No action needed.",
    )
