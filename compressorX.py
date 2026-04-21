import os
import subprocess
import pikepdf
import tempfile
import shutil
import streamlit as st

st.write("App loaded successfully.")

# -----------------------------
# Ghostscript (Linux-compatible)
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

    subprocess.run(command, check=False)


# -----------------------------
# PikePDF optimization
# -----------------------------
def optimize_with_pikepdf(input_path, output_path):
    with pikepdf.open(input_path) as pdf:
        pdf.save(output_path, compress_streams=True)


# -----------------------------
# QPDF linearization
# -----------------------------
def linearize_with_qpdf(input_path, output_path):
    subprocess.run(["qpdf", "--linearize", input_path, output_path], check=False)


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

            # Step 1: Ghostscript
            gs_compress(current_input, gs_out, level)

            # Step 2: PikePDF
            optimize_with_pikepdf(gs_out, pike_out)

            # Step 3: QPDF
            linearize_with_qpdf(pike_out, final_out)

            size_mb = os.path.getsize(final_out) / (1024 * 1024)

            if size_mb <= target_mb:
                break

            current_input = final_out

        safe_output = os.path.abspath(f"compressed_{level_used}.pdf")
        shutil.copy(final_out, safe_output)

        return safe_output, size_mb, level_used

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
