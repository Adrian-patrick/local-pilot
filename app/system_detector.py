"""System hardware detection for automatic LLM model selection.

Detects GPU type/VRAM, total RAM, and CPU to recommend the best
Ollama model that fits the user's hardware.
"""

from __future__ import annotations

import logging
import subprocess
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

# ── Model tiers based on VRAM availability ───────────────────────────────
# Each entry: (min_vram_gb, model_tag, description)
MODEL_TIERS: list[tuple[float, str, str]] = [
    (10.0, "qwen2.5:14b", "14B — Best quality, needs ≥10GB VRAM"),
    (5.0,  "qwen3:latest",  "Qwen 3 — Fast and efficient for mid-range GPUs"),
    (3.0,  "phi3:3.8b",   "3.8B — Lightweight, good for limited VRAM"),
    (0.0,  "qwen2.5:1.5b", "1.5B — Minimal resources, CPU-friendly"),
]


@dataclass
class SystemInfo:
    """Detected hardware capabilities."""

    gpu_name: str
    gpu_vram_gb: float
    total_ram_gb: float
    cpu_name: str
    cpu_cores: int

    @property
    def recommended_model(self) -> str:
        """Return the best model tag for this hardware."""
        effective_vram = self.gpu_vram_gb
        # If no dedicated GPU, use ~25% of RAM as a rough CPU-inference budget
        if effective_vram < 1.0:
            effective_vram = self.total_ram_gb * 0.25

        for min_vram, model, _desc in MODEL_TIERS:
            if effective_vram >= min_vram:
                return model

        return MODEL_TIERS[-1][1]  # smallest fallback

    @property
    def recommended_model_description(self) -> str:
        """Human-readable description of the recommended model."""
        model = self.recommended_model
        for _, tag, desc in MODEL_TIERS:
            if tag == model:
                return desc
        return model


def _detect_nvidia_vram() -> tuple[str, float]:
    """Try nvidia-smi to get GPU name and VRAM in GB."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                name = parts[0]
                vram_mb = float(parts[1])
                return name, vram_mb / 1024.0
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        log.debug("nvidia-smi detection failed: %s", exc)
    return "", 0.0


def _detect_wmi_gpu() -> tuple[str, float]:
    """Fallback: use Windows WMI to detect GPU."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_VideoController | "
                "Where-Object { $_.Name -notmatch 'Intel' } | "
                "Select-Object -First 1 | "
                "ForEach-Object { \"$($_.Name),$($_.AdapterRAM)\" })",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                name = parts[0].strip()
                try:
                    ram_bytes = int(parts[1].strip())
                    return name, ram_bytes / (1024 ** 3)
                except ValueError:
                    return name, 0.0
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        log.debug("WMI GPU detection failed: %s", exc)
    return "", 0.0


def _detect_ram_gb() -> float:
    """Detect total system RAM in GB."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip()) / (1024 ** 3)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        log.debug("RAM detection failed: %s", exc)
    return 0.0


def _detect_cpu() -> tuple[str, int]:
    """Detect CPU name and core count."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 | "
                "ForEach-Object { \"$($_.Name),$($_.NumberOfCores)\" })",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            name = parts[0].strip() if parts else "Unknown"
            cores = int(parts[1].strip()) if len(parts) > 1 else 0
            return name, cores
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        log.debug("CPU detection failed: %s", exc)
    return "Unknown", 0


def detect_system() -> SystemInfo:
    """Run all hardware detections and return a SystemInfo summary."""
    # GPU: try nvidia-smi first (most accurate), then WMI fallback
    gpu_name, gpu_vram = _detect_nvidia_vram()
    if gpu_vram < 0.5:
        wmi_name, wmi_vram = _detect_wmi_gpu()
        if wmi_name:
            gpu_name = wmi_name
            gpu_vram = max(gpu_vram, wmi_vram)

    ram_gb = _detect_ram_gb()
    cpu_name, cpu_cores = _detect_cpu()

    info = SystemInfo(
        gpu_name=gpu_name or "No dedicated GPU detected",
        gpu_vram_gb=round(gpu_vram, 1),
        total_ram_gb=round(ram_gb, 1),
        cpu_name=cpu_name,
        cpu_cores=cpu_cores,
    )
    log.info(
        "System detected: GPU=%s (%.1fGB), RAM=%.1fGB, CPU=%s (%d cores) → model=%s",
        info.gpu_name, info.gpu_vram_gb, info.total_ram_gb,
        info.cpu_name, info.cpu_cores, info.recommended_model,
    )
    return info
