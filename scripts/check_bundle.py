"""Verify the checked-in, browser-tested artifact without rebuilding it in CI."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web/amado"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    m = json.loads((APP / "manifest.json").read_text(encoding="utf-8"))
    assert sha(ROOT / "engine.py") == sha(APP / "engine.py") == m["core_sha256"]
    assert sha(APP / "bridge.py") == m["bridge_sha256"]
    assert sha(APP / "assets/base.zip") == m["base_zip_sha256"]
    for name, digest in m["files"].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in m["frontend_sha256"].items():
        assert sha(APP / name) == digest, name
    for name, digest in m.get("site_assets_sha256", {}).items():
        assert sha(ROOT / "web" / name) == digest, name
    for name, item in m["runtime"].items():
        assert sha(APP / "runtime" / name) == item["sha256"], name
    for name, digest in m["license_notices"].items():
        assert sha(APP / "runtime" / name) == digest, name
    with zipfile.ZipFile(APP / "assets/base.zip") as bundle:
        for name in bundle.namelist():
            path = (ROOT / name).resolve()
            assert path.is_relative_to(ROOT), name
            assert hashlib.sha256(bundle.read(name)).hexdigest() == sha(path), name
    print(json.dumps({"passed": True, "version": m["version"], "bundle_sha256": m["base_zip_sha256"], "policy": "Deploy the exact tested artifact, not a platform-specific rebuild."}))


if __name__ == "__main__":
    main()
