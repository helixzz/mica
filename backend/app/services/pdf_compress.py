"""Shrink scanned PDFs on upload.

Contracts arrive as scans: a handful of pages, one big image per page, tens of
megabytes. Ghostscript re-encodes those page images at a lower resolution and
JPEG quality, which is where the win is — the page stays legible while the file
drops by an order of magnitude.

Two safety rules:

* Only PDFs are touched, and only when the tool exists on the host. A missing
  ghostscript degrades to storing the original, never to failing the upload.
* The result is kept only if it is meaningfully smaller. Plenty of PDFs are
  already optimised, and re-encoding those would just add artifacts.

The trade-off is tunable from ``system_parameters`` (``pdf_compress.*``) so it can
be adjusted against real documents without shipping a release.

Measured on a synthetic 3-page, 300 dpi scan (7.8 MB): 200 dpi / q75 → 1.0 MB
(7.7x), 150 dpi / q68 → 0.75 MB (10.4x). Getting that second number right depends
on overriding the ``/ebook`` preset's 1.5x downsample threshold, otherwise a
300 dpi scan quietly survives a 200 dpi request.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.system_params import system_params

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
# Keep the compressed result only when it saves at least 5%.
_WORTH_KEEPING = 0.95
_TIMEOUT_SECONDS = 120
_MIN_DPI = 96
_MIN_QUALITY = 40


def _refinement_ladder(dpi: int, quality: int) -> list[tuple[int, int]]:
    """Fallbacks used only when a target size was requested and missed.

    Resolution carries the win (200 -> 120 dpi measured 2.8x further on a 300 dpi
    scan), so step that down and lower the quality. Grayscale is deliberately not
    part of the ladder: contracts carry red seals, and losing them is a visible
    change nobody asked for.
    """
    return [
        (max(_MIN_DPI, int(dpi * 0.8)), max(_MIN_QUALITY, quality - 10)),
        (max(_MIN_DPI, int(dpi * 0.6)), max(_MIN_QUALITY, quality - 20)),
    ]


async def compress_pdf_if_worthwhile(db: AsyncSession, content: bytes, content_type: str) -> bytes:
    """Return the bytes to store: compressed when it helps, unchanged otherwise.

    One pass at the configured resolution/quality/colour space. When a target
    size is configured and the first pass misses it, a short ladder of harder
    settings is tried — the same idea as the "expected output size" mode in
    online tools, within a bounded number of runs.
    """
    if content_type != PDF_MIME or not content.startswith(b"%PDF"):
        return content
    try:
        if not await system_params.get_bool_or(db, "pdf_compress.enabled", True):
            return content
        if shutil.which("gs") is None:
            logger.debug("ghostscript not installed; storing PDF as-is")
            return content
        dpi = await system_params.get_int_or(db, "pdf_compress.image_dpi", 200)
        quality = await system_params.get_int_or(db, "pdf_compress.jpeg_quality", 65)
        grayscale = await system_params.get_bool_or(db, "pdf_compress.grayscale", False)
        target_mb = await system_params.get_int_or(db, "pdf_compress.target_size_mb", 0)
    except Exception:
        logger.warning("could not read pdf compression settings", exc_info=True)
        return content

    try:
        best = await _run_ghostscript(content, dpi=dpi, quality=quality, grayscale=grayscale)
    except Exception:
        logger.warning("pdf compression failed; keeping the original bytes", exc_info=True)
        return content

    target_bytes = target_mb * 1024 * 1024 if target_mb > 0 else 0
    if target_bytes and best and len(best) > target_bytes:
        for step_dpi, step_quality in _refinement_ladder(dpi, quality):
            try:
                candidate = await _run_ghostscript(
                    content, dpi=step_dpi, quality=step_quality, grayscale=grayscale
                )
            except Exception:
                logger.warning("pdf refinement step failed", exc_info=True)
                break
            if candidate and len(candidate) < (len(best) if best else len(content)):
                best = candidate
            if best and len(best) <= target_bytes:
                break

    if best is None or len(best) >= len(content) * _WORTH_KEEPING:
        return content
    logger.info(
        "pdf compressed %d -> %d bytes (dpi=%s, jpegq=%s, gray=%s, target=%sMB)",
        len(content),
        len(best),
        dpi,
        quality,
        grayscale,
        target_mb or "-",
    )
    return best


async def _run_ghostscript(
    content: bytes, *, dpi: int, quality: int, grayscale: bool = False
) -> bytes | None:
    with tempfile.TemporaryDirectory() as workspace:
        source = Path(workspace) / "in.pdf"
        target = Path(workspace) / "out.pdf"
        source.write_bytes(content)

        command = [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.5",
            # /ebook gives a sane baseline (image re-encoding on); the resolution
            # and quality below are the parts we actually tune.
            "-dPDFSETTINGS=/ebook",
            "-dColorImageDownsampleThreshold=1.0",
            "-dGrayImageDownsampleThreshold=1.0",
            f"-dColorImageResolution={dpi}",
            f"-dGrayImageResolution={dpi}",
            f"-dJPEGQ={quality}",
            *(
                # Colour scans keep red seals legible, so this stays opt-in; when
                # it is on, RGB -> gray removes two thirds of the image data.
                ["-sColorConversionStrategy=Gray", "-dProcessColorModel=/DeviceGray"]
                if grayscale
                else []
            ),
            f"-sOutputFile={target}",
            str(source),
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(process.wait(), timeout=_TIMEOUT_SECONDS)
        except TimeoutError:
            process.kill()
            await process.wait()
            logger.warning("ghostscript timed out after %ss", _TIMEOUT_SECONDS)
            return None

        if process.returncode != 0 or not target.exists():
            return None
        return target.read_bytes()
