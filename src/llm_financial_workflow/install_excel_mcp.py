from __future__ import annotations

import argparse
import json
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path


LATEST_RELEASE_API = "https://api.github.com/repos/sbroenne/mcp-server-excel/releases/latest"
ASSET_SUFFIX = "-windows.zip"
ASSET_PREFIX = "ExcelMcp-MCP-Server-"
EXECUTABLE_NAME = "mcp-excel.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and install the Excel MCP server executable for this project."
    )
    parser.add_argument(
        "--install-dir",
        default=None,
        help="Directory where mcp-excel.exe will be installed. Defaults to <repo>/tools/excel-mcp.",
    )
    parser.add_argument(
        "--from-zip",
        default=None,
        help="Install from an existing release ZIP instead of downloading from GitHub.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing mcp-excel.exe.",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_install_dir() -> Path:
    return repo_root() / "tools" / "excel-mcp"


def executable_path(install_dir: Path) -> Path:
    return install_dir / EXECUTABLE_NAME


def fetch_latest_asset_url() -> str:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "elite-secretary-installer",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assets = payload.get("assets", [])
    for asset in assets:
        name = asset.get("name", "")
        if name.startswith(ASSET_PREFIX) and name.endswith(ASSET_SUFFIX):
            download_url = asset.get("browser_download_url")
            if download_url:
                return download_url

    raise RuntimeError("Could not find a Windows MCP Server ZIP asset in the latest GitHub release.")


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "elite-secretary-installer"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def extract_executable(zip_path: Path, install_dir: Path, force: bool) -> Path:
    install_dir.mkdir(parents=True, exist_ok=True)
    target_path = executable_path(install_dir)

    if target_path.exists() and not force:
        raise FileExistsError(
            f"{target_path} already exists. Re-run with --force to replace it."
        )

    with zipfile.ZipFile(zip_path) as archive:
        member_name = next(
            (
                name
                for name in archive.namelist()
                if Path(name).name.lower() == EXECUTABLE_NAME.lower()
            ),
            None,
        )
        if not member_name:
            raise RuntimeError(f"{EXECUTABLE_NAME} was not found inside {zip_path}.")

        with archive.open(member_name) as source, target_path.open("wb") as destination:
            shutil.copyfileobj(source, destination)

    target_path.chmod(target_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target_path


def install_from_zip(zip_path: Path, install_dir: Path, force: bool) -> Path:
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")
    return extract_executable(zip_path, install_dir, force)


def install_from_release(install_dir: Path, force: bool) -> Path:
    with tempfile.TemporaryDirectory(prefix="excel-mcp-install-") as temp_dir:
        zip_path = Path(temp_dir) / "excel-mcp-release.zip"
        asset_url = fetch_latest_asset_url()
        download_file(asset_url, zip_path)
        return extract_executable(zip_path, install_dir, force)


def main() -> None:
    args = parse_args()
    install_dir = Path(args.install_dir).resolve() if args.install_dir else default_install_dir()

    if args.from_zip:
        installed_path = install_from_zip(Path(args.from_zip).resolve(), install_dir, args.force)
    else:
        installed_path = install_from_release(install_dir, args.force)

    print(f"Installed Excel MCP executable: {installed_path}")
    print("If you use a custom path, set EXCEL_MCP_COMMAND to that executable before running the workflow.")


if __name__ == "__main__":
    main()
