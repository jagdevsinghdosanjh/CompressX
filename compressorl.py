import os
import subprocess
import pikepdf
import tempfile
import shutil
import time


def gs_compress(input_path, output_path, quality):
    quality_map = {
        "high": "/ebook",
        "medium": "/screen",
        "aggressive": "/screen",
        "very_aggressive": "/screen"
    }

    gs_quality = quality_map.get(quality, "/ebook")

    # Extra compression for very aggressive mode
    extra_flags = ""
    if quality == "very_aggressive":
        extra_flags = (
            "-dDownsampleColorImages=true "
            "-dColorImageResolution=100 "
            "-dDownsampleGrayImages=true "
            "-dGrayImageResolution=100 "
            "-dDownsampleMonoImages=true "
            "-dMonoImageResolution=100 "
            "-dJPEGQ=50 "
        )

    command = (
        f"gswin64c "
        f"-sDEVICE=pdfwrite "
        f"-dCompatibilityLevel=1.4 "
        f"-dPDFSETTINGS={gs_quality} "
        f"{extra_flags}"
        f"-dNOPAUSE -dQUIET -dBATCH "
        f"-sOutputFile=\"{output_path}\" "
        f"\"{input_path}\""
    )

    subprocess.run(command, shell=True)


def optimize_with_pikepdf(input_path, output_path):
    with pikepdf.open(input_path) as pdf:
        pdf.save(output_path, compress_streams=True)


def linearize_with_qpdf(input_path, output_path):
    os.system(f"qpdf --linearize \"{input_path}\" \"{output_path}\"")


def compress_to_target(input_path, target_mb=7):
    compression_levels = ["high", "medium", "aggressive", "very_aggressive"]

    tmp = tempfile.mkdtemp()

    # Initialize to satisfy Pylance
    final_out: str = ""
    size_mb: float = 0.0
    level_used: str = "high"

    try:
        current_input = input_path

        for level in compression_levels:
            level_used = level  # always assigned

            gs_out = os.path.join(tmp, f"gs_{level}.pdf")
            pike_out = os.path.join(tmp, f"pike_{level}.pdf")
            final_out = os.path.join(tmp, f"final_{level}.pdf")

            # Step 1: Ghostscript
            gs_compress(current_input, gs_out, level)
            time.sleep(0.2)

            # Step 2: PikePDF
            optimize_with_pikepdf(gs_out, pike_out)
            time.sleep(0.2)

            # Step 3: qpdf
            linearize_with_qpdf(pike_out, final_out)
            time.sleep(0.2)

            size_mb = os.path.getsize(final_out) / (1024 * 1024)

            if size_mb <= target_mb:
                break

            current_input = final_out

        # Safe output path
        safe_output = os.path.abspath(f"compressed_{level_used}.pdf")
        shutil.copy(final_out, safe_output)

        return safe_output, size_mb, level_used

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
