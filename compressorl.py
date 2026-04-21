import os
import subprocess
import tempfile
import shutil

try:
    import pikepdf
    PIKE_AVAILABLE = True
except Exception:
    PIKE_AVAILABLE = False


# -----------------------------
# Ghostscript compression
# -----------------------------
def gs_compress(input_path, output_path, quality):
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
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={gs_quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ] + extra_flags

    try:
        subprocess.run(command, check=False)
    except Exception:
        pass

    # Fallback if Ghostscript failed
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        shutil.copy(input_path, output_path)


# -----------------------------
# PikePDF optimization
# -----------------------------
def optimize_with_pikepdf(input_path, output_path):
    # If GS failed or file is bad, just copy forward
    if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
        shutil.copy(input_path, output_path)
        return

    if not PIKE_AVAILABLE:
        shutil.copy(input_path, output_path)
        return

    try:
        with pikepdf.open(input_path) as pdf:
            pdf.save(output_path, compress_streams=True)
    except Exception:
        shutil.copy(input_path, output_path)


# -----------------------------
# QPDF linearization
# -----------------------------
def linearize_with_qpdf(input_path, output_path):
    if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
        shutil.copy(input_path, output_path)
        return

    try:
        subprocess.run(["qpdf", "--linearize", input_path, output_path], check=False)
    except Exception:
        shutil.copy(input_path, output_path)


# -----------------------------
# Main compression pipeline
# -----------------------------
def compress_to_target(input_path, target_mb=7):
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

            # Step 1: Ghostscript (with fallback)
            gs_compress(current_input, gs_out, level)

            # Step 2: PikePDF (with fallback)
            optimize_with_pikepdf(gs_out, pike_out)

            # Step 3: QPDF (with fallback)
            linearize_with_qpdf(pike_out, final_out)

            if not os.path.exists(final_out) or os.path.getsize(final_out) == 0:
                # Absolute fallback: use previous input
                final_out = current_input

            size_mb = os.path.getsize(final_out) / (1024 * 1024)

            if size_mb <= target_mb:
                break

            current_input = final_out

        safe_output = os.path.abspath(f"compressed_{level_used}.pdf")
        shutil.copy(final_out, safe_output)

        return safe_output, size_mb, level_used

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
