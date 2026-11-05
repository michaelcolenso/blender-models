"""`bm assets pull` restores public release assets without `gh` auth, and still verifies checksums."""

import hashlib
import io
import json

import pytest

from bmodels import assets


def manifest(tmp_path, data):
    path = tmp_path / "release-assets.json"
    path.write_text(json.dumps({"repository": "owner/repo", "tag": "t-1", "storage": "release", "assets": [
        {"name": "a.bin", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}]}))
    return path


@pytest.fixture
def no_gh(monkeypatch, tmp_path):
    monkeypatch.setattr(assets, "BUILD", tmp_path / "build")
    monkeypatch.setattr(assets.shutil, "which", lambda name: None)


def test_falls_back_to_public_download_url(no_gh, tmp_path, monkeypatch):
    data = b"base scene"
    urls = []

    def urlopen(url, timeout):
        urls.append(url)
        return io.BytesIO(data)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    assets.pull(manifest(tmp_path, data))
    assert urls == ["https://github.com/owner/repo/releases/download/t-1/a.bin"]
    assert (tmp_path / "build/assets/t-1/a.bin").read_bytes() == data


def test_fallback_download_is_checksum_verified(no_gh, tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout: io.BytesIO(b"tampered"))
    with pytest.raises(ValueError, match="Release checksum mismatch"):
        assets.pull(manifest(tmp_path, b"base scene"))
