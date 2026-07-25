from __future__ import annotations

import subprocess

from src.utils.gpu_detect import detect_gpu


def test_detect_gpu_not_detected_when_nvidia_smi_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)

    info = detect_gpu()

    assert info.detected is False
    assert info.name is None


def test_detect_gpu_detected_when_nvidia_smi_succeeds(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/nvidia-smi")

    def _fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="Tesla T4\n", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    info = detect_gpu()

    assert info.detected is True
    assert info.name == "Tesla T4"


def test_detect_gpu_not_detected_when_nvidia_smi_exits_nonzero(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/nvidia-smi")

    def _fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="no devices found")

    monkeypatch.setattr("subprocess.run", _fake_run)

    info = detect_gpu()

    assert info.detected is False
    assert info.name is None


def test_detect_gpu_not_detected_on_subprocess_error(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/nvidia-smi")

    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=5)

    monkeypatch.setattr("subprocess.run", _raise)

    info = detect_gpu()

    assert info.detected is False
    assert info.name is None


def test_detect_gpu_not_detected_on_empty_output(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/nvidia-smi")

    def _fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="\n", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    info = detect_gpu()

    assert info.detected is False
    assert info.name is None
