import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from io import BytesIO
import platform
import os

# ---------- Page config ----------
st.set_page_config(
    page_title="Folder File Lister",
    page_icon="📁",
    layout="wide"
)

# ---------- Sidebar: Folder Settings ----------
with st.sidebar:
    st.header("Folder Settings")
    recursive = st.checkbox("Include subfolders (recursive)", value=False)
    show_hidden = st.checkbox("Show hidden files", value=False)

    st.markdown("---")
    st.markdown("**How to get folder path**")
    st.markdown("""
    **Windows:**  
    Open folder → click address bar → copy path

    **Mac / Linux:**  
    Right-click folder → Copy as Pathname
    """)

# ---------- Main Title ----------
st.title("📁 Folder File Lister")
st.markdown("List files from a folder and download the result as Excel")

# ---------- Notice ----------
st.info(
    """
    **Important:**  
    - Folder scanning **only works when you run the app locally** on your computer.  
    - It will **not work** on Streamlit Cloud because the cloud server cannot access your local hard drive.
    """,
    icon="ℹ️"
)

# ---------- Folder Section ----------
st.subheader("1. Select Folder")

col1, col2 = st.columns([4, 1])
with col1:
    folder_path = st.text_input(
        "Folder path",
        placeholder=r"Example: C:\Users\YourName\Desktop\Reports",
        label_visibility="collapsed",
        key="folder_input"
    )
with col2:
    if st.button("📂 Select Folder", use_container_width=True):
        st.toast("Please paste the folder path in the box on the left", icon="📋")

st.subheader("2. Scan & Download")
scan_btn = st.button("🔍 Scan Folder", type="primary", use_container_width=True)

# ---------- Helper functions ----------
def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

def is_windows_path(path_str: str) -> bool:
    """Check if the path looks like a Windows path (e.g. C:\\... or \\\\server\\...)"""
    path_str = path_str.strip()
    return (
        (len(path_str) >= 2 and path_str[1] == ":" and path_str[0].isalpha())  # C:\...
        or path_str.startswith("\\\\")  # UNC path
    )

def scan_folder(path_str: str, recursive: bool = False, show_hidden: bool = False):
    path_str = path_str.strip().strip('"').strip("'")

    # Detect if user pasted a Windows path while running on non-Windows (e.g. Streamlit Cloud)
    if is_windows_path(path_str) and platform.system() != "Windows":
        raise RuntimeError(
            "You pasted a **Windows path**, but this app is running on a Linux server "
            "(Streamlit Cloud).\n\n"
            "→ Folder scanning only works when you run the app **locally on your Windows computer**.\n\n"
            "Please download the code and run it with:\n"
            "```\nstreamlit run your_app.py\n```"
        )

    path = Path(path_str).expanduser()

    # Only resolve if it is a real existing path to avoid weird /mount/... behaviour
    try:
        path = path.resolve(strict=False)
    except Exception:
        pass

    if not path.exists():
        raise FileNotFoundError(
            f"Folder does not exist:\n`{path}`\n\n"
            "Possible reasons:\n"
            "1. You are running the app on Streamlit Cloud (it cannot see your local folders).\n"
            "2. The path is wrong or the folder was moved/deleted.\n"
            "3. You need to run the app **locally** on your computer."
        )

    if not path.is_dir():
        raise NotADirectoryError(f"This path is not a folder:\n`{path}`")

    files = []
    iterator = path.rglob("*") if recursive else path.glob("*")

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
                "Type": item.suffix[1:].lower() if item.suffix else "-",
                "Modified": modified.strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            continue

    files.sort(key=lambda x: x["Name"].lower())
    return files, str(path)

# ---------- Scan logic ----------
if scan_btn:
    if not folder_path.strip():
        st.warning("Please enter a folder path first.")
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

                st.success(f"Found **{len(df)}** files in:\n`{resolved_path}`")

                st.dataframe(
                    df[["#", "Name", "Path", "Size", "Type", "Modified"]],
                    use_container_width=True,
                    height=500
                )

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Files")

                st.download_button(
                    label="📥 Download Excel",
                    data=buffer.getvalue(),
                    file_name=f"folder_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"**Error:** {e}")

st.markdown("---")
st.caption("Made with Streamlit")
