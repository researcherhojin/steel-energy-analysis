"""Check that every locked dependency installs from prebuilt wheels on each supported platform.

    uv run python tools/check_platforms.py

Nothing is installed: uv resolves the lock file for each target and reports whether a binary
wheel exists for every package (no compiler needed). Exit status 1 if a supported target fails.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
SUPPORTED = {
    "x86_64-pc-windows-msvc": "Windows 64-bit (Intel/AMD)",
    "aarch64-pc-windows-msvc": "Windows ARM64",
    "x86_64-unknown-linux-gnu": "Linux x86_64 (Intel/AMD)",
    "aarch64-unknown-linux-gnu": "Linux ARM64",
    "x86_64-apple-darwin": "macOS Intel",
    "aarch64-apple-darwin": "macOS Apple Silicon",
}
UNSUPPORTED = {"i686-pc-windows-msvc": "Windows 32-bit (x86)"}


def check(target: str, requirements: Path, workdir: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["uv", "pip", "install", "--dry-run", "--python-version", PYTHON, "--python-platform", target,
         "--only-binary", ":all:", "-r", str(requirements), "--target", str(workdir / target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    output = result.stdout + result.stderr
    if "Would install" in output:
        return True, f"{sum(line.startswith(' + ') for line in output.splitlines())} packages"
    reason = next((line.strip() for line in output.splitlines() if "Because" in line), output.strip()[-200:])
    return False, reason


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        requirements = work / "requirements.txt"
        subprocess.run(["uv", "export", "--frozen", "--no-hashes", "--all-groups", "--no-emit-project",
                        "-o", str(requirements)], check=True, capture_output=True, cwd=ROOT)
        failed = False
        for targets, expect in ((SUPPORTED, True), (UNSUPPORTED, False)):
            for target, label in targets.items():
                ok, detail = check(target, requirements, work)
                status = "OK  " if ok else ("FAIL" if expect else "n/a ")
                print(f"{status}  {label:28s} {target:28s} {detail}")
                failed |= expect and not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
