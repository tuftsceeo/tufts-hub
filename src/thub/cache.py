"""
Cache management for offline PyScript versions.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from platformdirs import user_cache_dir
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console()


def parse_version(version: str) -> tuple[int, int, int]:
    """
    Parse a CalVer version string into a tuple for comparison.

    Returns (year, month, patch) as integers.
    """
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def is_version_supported(version: str) -> bool:
    """
    Check if a PyScript version supports offline assets.

    Offline support started with version 2025.11.2.
    """
    try:
        version_tuple = parse_version(version)
        min_version = (2025, 11, 2)
        return version_tuple >= min_version
    except ValueError:
        return False


def get_cache_dir() -> Path:
    """
    Get the platform-specific cache directory for PyScript versions.

    Returns the cache directory path (creates it if needed).
    """
    cache_dir = Path(user_cache_dir("thub", "thub")) / "pyscript"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_offline_url(version: str) -> str:
    """
    Build the URL for an offline PyScript version.

    Special case: Version 2025.11.2 uses "offline.zip"
    All other versions use "offline_{version}.zip"

    Returns URL in format:
    https://pyscript.net/releases/{version}/offline[_{version}].zip
    """
    if version == "2025.11.2":
        return f"https://pyscript.net/releases/{version}/offline.zip"
    else:
        return f"https://pyscript.net/releases/{version}/offline_{version}.zip"


def get_cached_version(version: str) -> Optional[Path]:
    """
    Check if a specific PyScript version is cached.

    Returns the path to the pyscript directory if cached, None otherwise.
    """
    cache_dir = get_cache_dir()
    version_dir = cache_dir / version / "pyscript"

    if version_dir.exists() and version_dir.is_dir():
        # Verify core files exist.
        if (version_dir / "core.js").exists() and (
            version_dir / "core.css"
        ).exists():
            return version_dir

    return None


def list_cached_versions() -> list[str]:
    """
    List all cached PyScript versions.

    Returns sorted list of version strings (newest first).
    """
    cache_dir = get_cache_dir()

    versions = []
    for item in cache_dir.iterdir():
        if item.is_dir():
            # Check if it has valid pyscript directory.
            pyscript_dir = item / "pyscript"
            if pyscript_dir.exists() and (pyscript_dir / "core.js").exists():
                versions.append(item.name)

    # Sort by version (reverse to get newest first).
    # Assumes CalVer format YYYY.MM.PATCH.
    versions.sort(reverse=True)
    return versions


def get_latest_cached_version() -> Optional[Path]:
    """
    Get the latest cached PyScript version.

    Returns the path to the pyscript directory if any cached, None otherwise.
    """
    versions = list_cached_versions()
    if versions:
        return get_cached_version(versions[0])
    return None


def download_offline_version(version: str) -> Path:
    """
    Download and extract an offline PyScript version.

    Returns the path to the extracted pyscript directory.
    Raises httpx.HTTPError if download fails.
    Raises ValueError if version doesn't support offline assets.
    """
    # Check if version supports offline assets.
    if not is_version_supported(version):
        raise ValueError(
            f"PyScript version {version} does not support offline assets. "
            f"Offline support requires version 2025.11.2 or later."
        )

    cache_dir = get_cache_dir()
    version_dir = cache_dir / version
    pyscript_dir = version_dir / "pyscript"

    # If already cached, return it.
    if pyscript_dir.exists():  # pragma: no cover
        return pyscript_dir

    # Create version directory.
    version_dir.mkdir(parents=True, exist_ok=True)

    # Download with progress bar.
    url = get_offline_url(version)
    # Use consistent zip filename regardless of upstream naming.
    zip_path = version_dir / f"offline_{version}.zip"

    console.print(f"[cyan]Downloading PyScript {version}...[/cyan]")
    console.print(f"[dim]Saving to: {zip_path}[/dim]")

    try:
        with httpx.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading", total=total)

                with open(zip_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

        console.print("[green]Download complete![/green]")

        # Extract the zip file to a temporary location.
        console.print("[cyan]Extracting...[/cyan]")
        temp_extract = version_dir / "temp_extract"
        temp_extract.mkdir(exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_extract)

        # Find the pyscript directory in the extracted content.
        # The zip contains either "offline/pyscript/" or
        # "offline_VERSION/pyscript/" depending on version.
        extracted_dirs = list(temp_extract.iterdir())

        if not extracted_dirs:  # pragma: no cover
            raise ValueError("Zip file appears to be empty")

        # The extracted directory should contain a pyscript subdirectory.
        extracted_root = extracted_dirs[0]
        source_pyscript = extracted_root / "pyscript"

        if not source_pyscript.exists():  # pragma: no cover
            raise ValueError(
                f"Expected pyscript directory not found in {extracted_root}"
            )

        # Move pyscript directory to the correct location.
        shutil.move(str(source_pyscript), str(pyscript_dir))

        # Clean up temporary extraction directory and zip file.
        shutil.rmtree(temp_extract)
        zip_path.unlink()

        console.print(
            f"[green]PyScript {version} cached successfully![/green]"
        )

        return pyscript_dir

    except Exception as e:
        # Clean up on failure.
        if version_dir.exists():
            shutil.rmtree(version_dir)
        raise


def copy_pyscript_to_project(pyscript_dir: Path, project_dir: Path) -> None:
    """
    Copy the pyscript directory to a project directory.

    Copies ALL files and subdirectories from the cached pyscript directory
    to project_dir/pyscript/.
    """
    dest = project_dir / "pyscript"

    # Remove if already exists.
    if dest.exists():
        shutil.rmtree(dest)

    # Copy the directory.
    shutil.copytree(pyscript_dir, dest)
