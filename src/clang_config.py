"""
Cross-platform libclang setup for C static analysis (macOS and Linux).

Override paths with environment variables (see .env.example):
  LIBCLANG_PATH     — directory containing libclang.so / libclang.dylib
  CLANG_RESOURCE_DIR — passed to clang as -resource-dir when parsing
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

_CONFIGURED = False
_LIBCLANG_DIR: str | None = None


def _dir_has_libclang(lib_dir: Path) -> bool:
    if not lib_dir.is_dir():
        return False
    for pat in ("libclang.so*", "libclang.dylib", "libclang.dll"):
        if any(lib_dir.glob(pat)):
            return True
    return False


def _libclang_dir_candidates() -> list[Path]:
    env = os.environ.get("LIBCLANG_PATH", "").strip()
    if env:
        return [Path(env).expanduser().resolve()]

    candidates: list[Path] = []
    if sys.platform == "darwin":
        candidates.extend(
            [
                Path("/opt/homebrew/opt/llvm/lib"),
                Path("/usr/local/opt/llvm/lib"),
            ]
        )
    else:
        for pattern in (
            "/usr/lib/llvm-*/lib",
            "/usr/lib64/llvm-*/lib",
            "/usr/lib/x86_64-linux-gnu",
            "/usr/lib/aarch64-linux-gnu",
        ):
            candidates.extend(Path(p) for p in glob.glob(pattern))
        try:
            llvm_config = shutil.which("llvm-config")
            if llvm_config:
                out = subprocess.check_output(
                    [llvm_config, "--libdir"], text=True, stderr=subprocess.DEVNULL
                ).strip()
                candidates.append(Path(out))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return candidates


def configure_libclang() -> str:
    """
    Set libclang's shared-library search path. Idempotent.
    Returns the directory that was configured.
    Raises RuntimeError with install hints if no library is found.
    """
    global _CONFIGURED, _LIBCLANG_DIR
    if _CONFIGURED and _LIBCLANG_DIR:
        return _LIBCLANG_DIR

    from clang.cindex import Config

    for lib_dir in _libclang_dir_candidates():
        if _dir_has_libclang(lib_dir):
            Config.set_library_path(str(lib_dir))
            _CONFIGURED = True
            _LIBCLANG_DIR = str(lib_dir)
            return _LIBCLANG_DIR

    hints = (
        "libclang not found. Install LLVM/libclang, then either:\n"
        "  - set LIBCLANG_PATH in .env to the directory with libclang.so (Linux)\n"
        "    or libclang.dylib (macOS), or\n"
        "  - macOS: brew install llvm\n"
        "  - Debian/Ubuntu: sudo apt install clang libclang-dev\n"
    )
    raise RuntimeError(hints)


def libclang_usable() -> bool:
    try:
        configure_libclang()
        from clang.cindex import Index

        Index.create()
        return True
    except Exception:
        return False


def _darwin_sdk_args() -> list[str]:
    sdk = subprocess.check_output(
        ["xcrun", "--show-sdk-path"], text=True, stderr=subprocess.DEVNULL
    ).strip()
    return ["-isysroot", sdk, "-I", f"{sdk}/usr/include"]


def _linux_resource_args() -> list[str]:
    env = os.environ.get("CLANG_RESOURCE_DIR", "").strip()
    if env:
        return ["-resource-dir", env]

    clang = shutil.which("clang") or shutil.which("clang-18") or shutil.which("clang-17")
    if clang:
        try:
            rd = subprocess.check_output(
                [clang, "-print-resource-dir"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if rd:
                return ["-resource-dir", rd]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return []


def clang_parse_args() -> list[str]:
    """Compiler flags passed to libclang when parsing translation units."""
    base = ["-x", "c", "-std=c11"]
    if sys.platform == "darwin":
        try:
            return base + _darwin_sdk_args()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "xcrun not found. On macOS install Xcode Command Line Tools: "
                "xcode-select --install"
            ) from e
    return base + _linux_resource_args()


def clang_platform_summary() -> str:
    """One-line status for logging at pipeline start."""
    try:
        lib = configure_libclang()
    except RuntimeError as e:
        return f"libclang: NOT CONFIGURED ({e})"
    plat = "macOS" if sys.platform == "darwin" else sys.platform
    return f"libclang: {lib} ({plat})"
