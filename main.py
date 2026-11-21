"""Entrypoint exporter for news-image-20261121."""

import hashlib
import logging
import os
import shutil
import sys
from typing import Optional, Sequence

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("news-image-exporter")

PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"


def compute_sha256(filepath: str) -> str:
    """Compute the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_image_integrity(filepath: str) -> bool:
    """Validate that the file exists, is non-empty, and possesses a valid PNG signature."""
    try:
        if not os.path.isfile(filepath):
            logger.error("Integrity check failed: '%s' is not a file", filepath)
            return False

        size_bytes = os.path.getsize(filepath)
        if size_bytes == 0:
            logger.error("Integrity check failed: '%s' is an empty file (0 bytes)", filepath)
            return False

        with open(filepath, "rb") as f:
            header = f.read(len(PNG_MAGIC_BYTES))
            if header != PNG_MAGIC_BYTES:
                logger.error(
                    "Integrity check failed: '%s' missing standard PNG magic header", filepath
                )
                return False

        checksum = compute_sha256(filepath)
        logger.info(
            "Integrity verified for '%s' (Size: %d bytes, SHA-256: %s)",
            filepath,
            size_bytes,
            checksum,
        )
        return True
    except (OSError, IOError) as exc:
        logger.error("I/O error during integrity verification for '%s': %s", filepath, exc)
        return False


def find_entry_file(candidate_dirs: Optional[Sequence[str]] = None) -> Optional[str]:
    """Scan candidate locations for the entry image file."""
    if candidate_dirs is None:
        candidate_dirs = [
            os.path.dirname(os.path.abspath(__file__)),
            "/bot",
            os.getcwd(),
        ]

    for directory in candidate_dirs:
        target = os.path.join(directory, "entry.png")
        logger.debug("Checking path candidate: %s", target)
        if os.path.isfile(target):
            logger.info("Found entry image candidate at: %s", target)
            if verify_image_integrity(target):
                return target
            logger.warning("Candidate at '%s' failed integrity checks, skipping", target)

    return None


def main() -> None:
    """Execute exporter verification and copy operation with complete error handling."""
    logger.info("Starting news-image-20261121 export pipeline")
    source_path: Optional[str] = find_entry_file()
    if not source_path:
        logger.error("Fatal: Valid entry.png could not be found or verified in any candidate path")
        sys.exit(1)

    output_dir: str = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        logger.error("Fatal: Failed to create output directory '%s': %s", output_dir, exc)
        sys.exit(2)

    destination_path: str = os.path.join(output_dir, "entry.png")

    try:
        shutil.copy2(source_path, destination_path)
        logger.info("Copied file to destination: %s", destination_path)
    except (shutil.Error, OSError, IOError) as exc:
        logger.error("Fatal: Failed to copy file from '%s' to '%s': %s", source_path, destination_path, exc)
        sys.exit(3)

    if not verify_image_integrity(destination_path):
        logger.error("Fatal: Destination file failed integrity check after copy")
        sys.exit(4)

    logger.info("Export pipeline completed successfully. Output verified at: %s", destination_path)


if __name__ == "__main__":
    main()
