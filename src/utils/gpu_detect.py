from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class GpuInfo:
    detected: bool
    name: str | None


def detect_gpu() -> GpuInfo:
    """Best-effort NVIDIA GPU detection via `nvidia-smi`, mirroring
    `deploy/setup_ec2.sh`'s own `command -v nvidia-smi` check. This is
    advisory information for an admin's backend choice, not a hard
    dependency - any failure (missing binary, non-zero exit, unexpected
    output) resolves to "not detected" rather than raising."""
    if shutil.which("nvidia-smi") is None:
        return GpuInfo(detected=False, name=None)

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return GpuInfo(detected=False, name=None)

    if result.returncode != 0:
        return GpuInfo(detected=False, name=None)

    first_line = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
    return GpuInfo(detected=bool(first_line), name=first_line or None)
