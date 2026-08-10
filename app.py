import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
st.set_page_config(
    page_title="Folder File Lister → Excel",
    page_icon="📁",
    layout="wide"
)
st.title("📁 Folder File Lister → Excel")
st.markdown("Enter a target folder path, list all files, and download the list as Excel.")
# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    recursive = st.checkbox("Include subfolders (recursive)", value=False)
    show_hidden = st.checkbox("Show hidden files", value=False)
    st.markdown("---")
    st.markdown("**How to use**")
    st.markdown("1. Type the full path of the folder")
    st.markdown("2. Click **Scan Folder**")
    st.markdown("3. Download the Excel file")
# ---------- Main input ----------
folder_path = st.text_input(
    "Target folder path",
    placeholder=r"C:\Users\YourName\Documents or /home/user/Documents",
    help="Enter the absolute path of the folder you want to scan"
)
col1, col2 = st.columns([1, 4])
with col1:
    scan_btn = st.button("🔍 Scan Folder", type="primary", use_container_width=True)
# ---------- Scan logic ----------
def scan_folder(path: str, recursive: bool = False, show_hidden: bool = False):
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Folder does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {path}")
    files = []
    if recursive:
        iterator = path.rglob("*")
    else:
        iterator = path.glob("*")
    for item in iterator:
        if not item.is_file():
            continue
        if not show_hidden and item.name.startswith("."):
            continue
        try:
            stat = item.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime)
            files.append({
                "Name": item.name,
                "Path": str(item.relative_to(path)),
                "Full Path": str(item),
                "Size (bytes)": size,
                "Size": format_size(size),
                "Type": item.suffix[1:].lower() if item.suffix else "—",
                "Modified": modified.strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            continue
    return files, str(path)
def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"
# ---------- Run scan ----------
if scan_btn:
    if not folder_path.strip():
        st.warning("Please enter a folder path.")
    else:
        try:
            with st.spinner("Scanning folder..."):
                files, resolved_path = scan_folder(
                    folder_path.strip(),
                    recursive=recursive,
                    show_hidden=show_hidden
                )
            if not files:
                st.info("No files found in this folder.")
            else:
                df = pd.DataFrame(files)
                df.insert(0, "#", range(1, len(df) + 1))
                st.success(f"Found **{len(df)}** files in: {resolved_path}")
                # Show table
                st.dataframe(
                    df[["#", "Name", "Path", "Size", "Type", "Modified"]],
                    use_container_width=True,
                    height=500
                )
                # Prepare Excel for download
                excel_buffer = pd.ExcelWriter("files.xlsx", engine="openpyxl")
                df.to_excel(excel_buffer, index=False, sheet_name="Files")
                excel_buffer.close()
                with open("files.xlsx", "rb") as f:
                    st.download_button(
                        label="📥 Download Excel",
                        data=f,
                        file_name=f"folder_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                # Clean up temporary file
                try:
                    os.remove("files.xlsx")
                except Exception:
                    pass
        except Exception as e:
            st.error(f"Error: {e}")
# ---------- Footer ----------
st.markdown("---")
st.caption("Made with Streamlit • List files from any folder and export to Excel")
