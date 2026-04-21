import os
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

import pikepdf


# -----------------------------
# Simple logger (stdout-friendly)
# -----------------------------
class Logger:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def log(self, msg: str):
        if self.enabled:
            print(f"[CompressX] {msg}")


logger = Logger(enabled=True)


# -----------------------------
# Tool detection (cached)
# -----------------------------
_GS_CMD = None
_QPDF_CMD = None


def detect_gs():
    global _GS_CMD
    if _GS_CMD is not None:
        return _GS_CMD

    candidates = ["gs", "gswin64c"]
    for c in candidates:
        try:
            subprocess.run([c, "-v"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
            _GS_CMD = c
            logger.log(f"Ghostscript detected: {c}")
            return _GS_CMD
        except Exception:
            continue

    logger.log("Ghostscript NOT found. Falling back to pikepdf-only.")
    _GS_CMD = None
    return None


def detect_qpdf():
    global _QPDF_CMD
    if _QPDF_CMD is not None:
        return _QPDF_CMD

    try:
        subprocess.run(["qpdf", "--version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
        _QPDF_CMD = "qpdf"
        logger.log("QPDF detected: qpdf")
        return _QPDF_CMD
    except Exception:
        logger.log("QPDF NOT found. Skipping linearization.")
        _QPDF_CMD = None
        return None


# -----------------------------
# Ghostscript compression
# -----------------------------
def gs_compress(input_path, output_path, quality):
    gs_cmd = detect_gs()
    if gs_cmd is None:
        # No Ghostscript available; just copy input to output
        shutil.copy(input_path, output_path)
        return

    quality_map = {
        "high": "/ebook",
        "medium": "/screen",
        "aggressive": "/screen",
        "very_aggressive": "/screen"
    }

    gs_quality = quality_map.get(quality, "/ebook")

    extra_flags = []
    if quality == "very_aggressive":
        extra_flags = [
            "-dDownsampleColorImages=true",
            "-dColorImageResolution=100",
            "-dDownsampleGrayImages=true",
            "-dGrayImageResolution=100",
            "-dDownsampleMonoImages=true",
            "-dMonoImageResolution=100",
            "-dJPEGQ=50"
        ]

    command = [
        gs_cmd,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={gs_quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ] + extra_flags

    logger.log(f"Running Ghostscript ({quality}) on {os.path.basename(input_path)}")
    try:
        subprocess.run(command, check=False)
    except Exception as e:
        logger.log(f"Ghostscript error: {e}. Copying input to output.")
        shutil.copy(input_path, output_path)


# -----------------------------
# PikePDF optimization
# -----------------------------
def optimize_with_pikepdf(input_path, output_path):
    logger.log(f"PikePDF optimizing {os.path.basename(input_path)}")
    try:
        with pikepdf.open(input_path) as pdf:
            pdf.save(output_path, compress_streams=True)
    except Exception as e:
        logger.log(f"PikePDF error: {e}. Copying input to output.")
        shutil.copy(input_path, output_path)


# -----------------------------
# QPDF linearization
# -----------------------------
def linearize_with_qpdf(input_path, output_path):
    qpdf_cmd = detect_qpdf()
    if qpdf_cmd is None:
        shutil.copy(input_path, output_path)
        return

    logger.log(f"QPDF linearizing {os.path.basename(input_path)}")
    try:
        subprocess.run([qpdf_cmd, "--linearize", input_path, output_path],
                       check=False)
    except Exception as e:
        logger.log(f"QPDF error: {e}. Copying input to output.")
        shutil.copy(input_path, output_path)


# -----------------------------
# Core single-file compression
# -----------------------------
def compress_to_target(input_path, target_mb=7):
    """
    Compress a single PDF to <= target_mb (best effort).
    Returns: (output_path, size_mb, level_used)
    """
    compression_levels = ["high", "medium", "aggressive", "very_aggressive"]

    tmp = tempfile.mkdtemp()
    final_out = ""
    size_mb = 0.0
    level_used = "high"

    try:
        current_input = input_path

        for level in compression_levels:
            level_used = level

            gs_out = os.path.join(tmp, f"gs_{level}.pdf")
            pike_out = os.path.join(tmp, f"pike_{level}.pdf")
            final_out = os.path.join(tmp, f"final_{level}.pdf")

            # Step 1: Ghostscript (or copy if unavailable)
            gs_compress(current_input, gs_out, level)

            # Step 2: PikePDF
            optimize_with_pikepdf(gs_out, pike_out)

            # Step 3: QPDF
            linearize_with_qpdf(pike_out, final_out)

            size_mb = os.path.getsize(final_out) / (1024 * 1024)

            logger.log(
                f"{os.path.basename(input_path)} | Level={level} | Size={size_mb:.2f} MB"
            )

            if size_mb <= target_mb:
                break

            current_input = final_out

        safe_output = os.path.abspath(f"compressed_{level_used}_{os.path.basename(input_path)}")
        shutil.copy(final_out, safe_output)

        return safe_output, size_mb, level_used

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# -----------------------------
# Optional: batch compression with parallelism
# -----------------------------
def compress_batch(
    input_paths,
    target_mb=7,
    max_workers=4,
    progress_callback=None,
):
    """
    Compress multiple PDFs in parallel (thread-based).
    input_paths: list of file paths
    progress_callback: callable(done_count, total_count) for UI (e.g., Streamlit progress)
    Returns: list of dicts with results.
    """
    results = []
    total = len(input_paths)
    done = 0

    def _wrap(path):
        out, size_mb, level = compress_to_target(path, target_mb=target_mb)
        return {
            "input": path,
            "output": out,
            "compressed_mb": size_mb,
            "level": level,
        }

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(_wrap, p): p for p in input_paths}
        for fut in as_completed(future_map):
            res = fut.result()
            results.append(res)
            done += 1
            if progress_callback is not None:
                progress_callback(done, total)

    return results
