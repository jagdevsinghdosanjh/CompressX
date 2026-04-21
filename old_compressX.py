import streamlit as st
import os
import zipfile
import time
import pandas as pd
from compressorl import compress_to_target

# ---------- Page config ----------
st.set_page_config(page_title="CompressX – Bulk PDF Compressor <7MB", layout="centered")

# ---------- Branding header ----------
st.markdown("""
<div style='text-align:center; padding:20px'>
    <h1 style='color:#5A4FF3; margin-bottom:4px;'>CompressX</h1>
    <h3 style='margin-top:0;'>Bulk PDF Compressor &lt;7MB Auto‑Target</h3>
    <p>Smaller PDFs. Bigger Productivity.</p>
    <p style='color:gray; font-size:13px;'>Version 1.0.0</p>
</div>
""", unsafe_allow_html=True)

# ---------- Plan selection ----------
st.sidebar.title("CompressX Plans")

plan = st.sidebar.radio(
    "Select a plan:",
    ["Basic – ₹99/month", "Pro – ₹199/month", "Lifetime – ₹999 (One‑time)"]
)

if plan == "Basic – ₹99/month":
    max_files = 50
elif plan == "Pro – ₹199/month":
    max_files = 500
else:
    max_files = 10000  # effectively unlimited

# ---------- Main title ----------
st.title("📄 Bulk PDF Compressor (Auto Target <7MB)")

# ---------- File upload ----------
uploaded_files = st.file_uploader(
    "Upload multiple PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f"Total files uploaded: **{len(uploaded_files)}**")

    # Enforce plan limit
    if len(uploaded_files) > max_files:
        st.error(f"Your current plan allows only {max_files} files at a time.")
        st.stop()

    if st.button("Start Bulk Compression"):
        results = []
        output_files = []

        total_original = 0.0
        total_compressed = 0.0

        start_time = time.time()

        for file in uploaded_files:
            st.info(f"Processing: {file.name}")

            # Save input file
            input_path = f"input_{file.name}"
            with open(input_path, "wb") as f:
                f.write(file.getvalue())

            original_size = len(file.getvalue()) / (1024 * 1024)
            total_original += original_size

            # Compress
            output_path, compressed_size, level_used = compress_to_target(
                input_path,
                target_mb=7
            )
            total_compressed += compressed_size

            # Calculate percentage
            percent = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0.0

            # Collect results
            results.append({
                "name": file.name,
                "original": original_size,
                "compressed": compressed_size,
                "percent": percent,
                "mode": level_used,
                "path": output_path
            })

            output_files.append(output_path)

        end_time = time.time()
        duration = end_time - start_time

        st.success("Bulk compression completed.")

        # ---------- Per-file summary ----------
        st.subheader("📊 Compression Summary")

        for r in results:
            st.write(f"### {r['name']}")
            st.write(f"- Original: **{r['original']:.2f} MB**")
            st.write(f"- Compressed: **{r['compressed']:.2f} MB**")
            st.write(f"- Compression Achieved: **{r['percent']:.2f}%**")
            st.write(f"- Mode Used: **{r['mode']}**")

            with open(r["path"], "rb") as f:
                st.download_button(
                    label=f"Download {r['name']}",
                    data=f.read(),
                    file_name=f"compressed_{r['name']}",
                    mime="application/pdf"
                )

        # ---------- Overall summary ----------
        total_percent = ((total_original - total_compressed) / total_original) * 100 if total_original > 0 else 0.0

        st.subheader("📘 Overall Compression Summary")
        st.write(f"- Total Files: **{len(results)}**")
        st.write(f"- Time Taken: **{duration:.2f} seconds**")
        st.write(f"- Total Original Size: **{total_original:.2f} MB**")
        st.write(f"- Total Compressed Size: **{total_compressed:.2f} MB**")
        st.write(f"- Total Compression Achieved: **{total_percent:.2f}%**")

        # ---------- CSV report ----------
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Compression Report (CSV)",
            csv,
            "compressx_report.csv",
            "text/csv"
        )

        # ---------- ZIP download ----------
        zip_name = "compressed_pdfs.zip"
        with zipfile.ZipFile(zip_name, "w") as zipf:
            for r in results:
                zipf.write(r["path"], arcname=f"compressed_{r['name']}")

        with open(zip_name, "rb") as f:
            st.download_button(
                label="⬇ Download All as ZIP",
                data=f.read(),
                file_name=zip_name,
                mime="application/zip"
            )

        # ---------- EXE download for Lifetime plan ----------
        if plan == "Lifetime – ₹999 (One‑time)":
            st.subheader("Offline Version")
            st.write("As a Lifetime user, you can download the offline EXE:")

            try:
                with open("CompressX_Setup.exe", "rb") as f:
                    st.download_button(
                        "Download Offline EXE",
                        f.read(),
                        "CompressX_Setup.exe"
                    )
            except FileNotFoundError:
                st.info("EXE will be available here once you place CompressX_Setup.exe in the app folder.")

# ---------- Footer ----------
st.markdown("""
<hr>
<div style='text-align:center; color:gray; padding:10px; font-size:13px;'>
    <p>CompressX — Bulk PDF Compressor</p>
    <p>Made in Punjab 🇮🇳</p>
    <p>Support: your-email | WhatsApp</p>
</div>
""", unsafe_allow_html=True)
