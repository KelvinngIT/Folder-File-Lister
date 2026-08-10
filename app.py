import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from io import BytesIO

st.set_page_config(
    page_title="Folder File Lister to Excel",
    page_icon="📁",
    layout="wide"
)

st.title("📁 Folder File Lister to Excel")
st.markdown("Select a folder path → list all files → download as Excel")

# ---------- Notice ----------
st.info(
    """
    **Note:** Streamlit cannot open a real folder picker dialog because of browser security.  
    Please **copy the full path** of your folder and paste it below.
    """,
    icon="ℹ️"
)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    recursive = st.checkbox("Include subfolders (recursive)", value=False)
    show_hidden = st.checkbox("Show hidden files", value=False)

    st.markdown("---")
    st.markdown("**How to get the folder path**")
    st.markdown("""
    **Windows:**
    1. Open the folder in File Explorer
    2. Click the address bar
    3. Copy the path (Ctrl + C)
    4. Paste it below

    **Mac / Linux:**
    1. Open the folder
    2. Right-click → “Copy as Pathname” (or similar)
    3. Paste it below
    """)

# ---------- Folder selection area ----------
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
    # This button just gives a visual "Select Folder" feeling
    # It focuses attention on the text input
    if st.button("📂 Select Folder", use_container_width=True):
        st.toast("Please paste the folder path in the box on the left", icon="📋")

# ---------- Scan button ----------
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


def scan_folder(path_str: str, recursive: bool = False, show_hidden: bool = False):
    path_str = path_str.strip().strip('"').strip("'")
    path = Path(path_str).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"Folder does not exist:\n`{path}`\n\n"
            "Please check the path and make sure you are running the app locally."
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


# ---------- Main logic ----------
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

                # Excel download
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
st.caption("Made with Streamlit • Must be run locally to access folders on your computer")
