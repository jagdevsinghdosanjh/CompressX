import streamlit as st
import os
import zipfile
import time
import pandas as pd
from compressor import compress_to_target

# ---------- Page config ----------
st.set_page_config(page_title="CompressX – Bulk PDF Compressor <7MB", layout="wide")

# ---------- Dark / Light mode toggle ----------
dark_mode = st.sidebar.toggle("Dark mode", value=False)

if dark_mode:
    st.markdown(
        """
        <style>
        body { background-color: #0f172a; color: #e5e7eb; }
        .stApp { background-color: #0f172a; }
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------- Branding header ----------
st.markdown("""
<div style='text-align:center; padding:20px'>
    <h1 style='color:#5A4FF3; margin-bottom:4px;'>CompressX</h1>
    <h3 style='margin-top:0;'>Bulk PDF Compressor &lt;7MB Auto‑Target</h3>
    <p>Smaller PDFs. Bigger Productivity.</p>
    <p style='color:gray; font-size:13px;'>Version 1.1.0</p>
</div>
""", unsafe_allow_html=True)

# ---------- License / activation (simple gate) ----------
st.sidebar.title("Activation")

license_key = st.sidebar.text_input("Enter license key (optional)", type="password")
licensed = license_key.strip() != ""  # placeholder logic

if licensed:
    st.sidebar.success("License activated (demo logic).")
else:
    st.sidebar.info("Running in unlicensed mode (demo).")

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

            # Band for color coding
            if percent >= 40:
                band = "High (≥40%)"
            elif percent >= 20:
                band = "Medium (20–40%)"
            else:
                band = "Low (<20%)"

            # Collect results
            results.append({
                "File": file.name,
                "Original_MB": round(original_size, 2),
                "Compressed_MB": round(compressed_size, 2),
                "Percent_Saved": round(percent, 2),
                "Band": band,
                "Mode": level_used,
                "Path": output_path
            })

            output_files.append(output_path)

        end_time = time.time()
        duration = end_time - start_time

        st.success("Bulk compression completed.")

        # ---------- DataFrame for UI / report ----------
        df = pd.DataFrame(results)

        # ---------- Per-file table (commercial UI) ----------
        st.subheader("📊 Compression Summary (Per File)")

        df_display = df[["File", "Original_MB", "Compressed_MB", "Percent_Saved", "Band", "Mode"]]
        st.dataframe(df_display, use_container_width=True)

        # ---------- Overall summary ----------
        total_percent = ((total_original - total_compressed) / total_original) * 100 if total_original > 0 else 0.0

        st.subheader("📘 Overall Compression Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Files", len(results))
        col2.metric("Total Original (MB)", f"{total_original:.2f}")
        col3.metric("Total Compressed (MB)", f"{total_compressed:.2f}")
        col4.metric("Total Saved (%)", f"{total_percent:.2f}")

        st.write(f"⏱ Time Taken: **{duration:.2f} seconds**")

        # ---------- Charts dashboard ----------
        st.subheader("📈 Compression Dashboard")

        chart_df = df[["File", "Percent_Saved"]].set_index("File")
        st.bar_chart(chart_df)

        size_df = df[["File", "Original_MB", "Compressed_MB"]].set_index("File")
        st.line_chart(size_df)

        # ---------- CSV report ----------
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Compression Report (CSV)",
            csv,
            "compressx_report.csv",
            "text/csv"
        )

        # ---------- Individual downloads ----------
        st.subheader("⬇ Download Individual Files")
        for _, row in df.iterrows():
            with open(row["Path"], "rb") as f:
                st.download_button(
                    label=f"Download {row['File']}",
                    data=f.read(),
                    file_name=f"compressed_{row['File']}",
                    mime="application/pdf"
                )

        # ---------- ZIP download ----------
        zip_name = "compressed_pdfs.zip"
        with zipfile.ZipFile(zip_name, "w") as zipf:
            for _, row in df.iterrows():
                zipf.write(row["Path"], arcname=f"compressed_{row['File']}")

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
