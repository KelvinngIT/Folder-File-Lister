import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from io import BytesIO
import os

# Google Auth libraries
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ---------- Page config ----------
st.set_page_config(
    page_title="Folder File Lister + Gmail",
    page_icon="📁",
    layout="wide"
)

# ---------- Google OAuth Config ----------
# You must create these in Google Cloud Console
CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID.apps.googleusercontent.com")
CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:8501")  # change when deployed

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly"
]

# ---------- Helper: Google Login ----------
def get_google_flow():
    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow


def login_with_google():
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    st.session_state["oauth_state"] = state
    st.markdown(f'<meta http-equiv="refresh" content="0; url={authorization_url}">', unsafe_allow_html=True)
    st.info("Redirecting to Google login...")


def handle_oauth_callback():
    query_params = st.query_params
    if "code" in query_params:
        try:
            flow = get_google_flow()
            flow.fetch_token(code=query_params["code"])
            credentials = flow.credentials

            st.session_state["credentials"] = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            }

            # Get user info
            service = build("oauth2", "v2", credentials=credentials)
            user_info = service.userinfo().get().execute()
            st.session_state["user"] = user_info

            # Clear the code from URL
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")


def get_credentials():
    if "credentials" not in st.session_state:
        return None
    creds_data = st.session_state["credentials"]
    return Credentials(
        token=creds_data["token"],
        refresh_token=creds_data.get("refresh_token"),
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=creds_data["scopes"]
    )


def logout():
    for key in ["credentials", "user", "oauth_state"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def get_recent_emails(max_results=10):
    creds = get_credentials()
    if not creds:
        return []

    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()

        headers = detail.get("payload", {}).get("headers", [])
        get_header = lambda name: next(
            (h["value"] for h in headers if h["name"].lower() == name.lower()), ""
        )

        emails.append({
            "From": get_header("From"),
            "Subject": get_header("Subject"),
            "Date": get_header("Date"),
            "Snippet": detail.get("snippet", "")
        })
    return emails


# ---------- Handle OAuth callback ----------
handle_oauth_callback()

# ---------- Sidebar: Login / User ----------
with st.sidebar:
    st.header("Account")

    if "user" in st.session_state:
        user = st.session_state["user"]
        st.success(f"Logged in as\n**{user.get('name', '')}**\n{user.get('email', '')}")
        if st.button("Logout", use_container_width=True):
            logout()
    else:
        st.info("Please login with your Gmail account")
        if st.button("Login with Gmail", type="primary", use_container_width=True):
            login_with_google()

    st.markdown("---")
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
st.title("📁 Folder File Lister + Gmail")
st.markdown("Login with Gmail → list files from a folder → download Excel / read emails")

# ---------- Notice ----------
st.info(
    """
    **Note:**  
    - Folder scanning only works when you run the app **locally**.  
    - Gmail features work both locally and on Streamlit Cloud.
    """,
    icon="ℹ️"
)

# ---------- Gmail Section (only after login) ----------
if "user" in st.session_state:
    st.subheader("📧 Gmail - Recent Emails")

    if st.button("Load Recent Emails", use_container_width=True):
        with st.spinner("Loading emails from your Gmail..."):
            try:
                emails = get_recent_emails(10)
                if emails:
                    df_emails = pd.DataFrame(emails)
                    st.dataframe(df_emails, use_container_width=True, height=300)

                    # Download emails as Excel
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        df_emails.to_excel(writer, index=False, sheet_name="Emails")
                    st.download_button(
                        label="📥 Download Emails as Excel",
                        data=buffer.getvalue(),
                        file_name=f"gmail_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.info("No emails found.")
            except Exception as e:
                st.error(f"Failed to load emails: {e}")

    st.markdown("---")

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


# ---------- Folder helper functions ----------
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
st.caption("Made with Streamlit • Gmail login via Google OAuth2")
