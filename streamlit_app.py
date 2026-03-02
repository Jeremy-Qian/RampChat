import json
import time
from datetime import datetime

import streamlit as st
from supabase.client import Client, create_client


def format_timestamp(iso_string):
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%Y.%m.%d, %I:%M %p")


SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

USERS = st.secrets.get("users", {})
AVATAR_OPTIONS = st.secrets.get("avatars", {}).get("options", ["😎"])
DEFAULT_AVATAR = st.secrets.get("avatars", {}).get("default", "😎")
st.badge(":material/science: Experimental", color="blue")
st.set_page_config(
    page_title="RampChat", page_icon="💬", initial_sidebar_state="collapsed"
)
st.markdown(
    """
<style>
.title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 3em;
    text-align: center;
    margin-bottom: 30px;
}
.subtitle {
    font-family: 'JetBrains Mono', monospace;
    text-align: center;
    color: #888;
}
.stToolbarActions {
    visibility: hidden!important;
}
</style>
<h1 class="title">RampChat</h1>
<p class="subtitle">Group Chat</p>
<div class="stToolbarActions st-emotion-cache-1p1m4ay eyud7442" data-testid="stToolbarActions" style="visibility: hidden;"></div>
""",
    unsafe_allow_html=True,
)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None


def login():

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In")

            if submit:
                if username in USERS and USERS[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    ensure_user_avatar(username)
                    st.rerun()
                else:
                    st.error("Invalid username or password")


def ensure_user_avatar(username):
    try:
        response = (
            supabase.table("user_avatars")
            .select("username")
            .eq("username", username)
            .execute()
        )
        if not response.data or len(response.data) == 0:
            supabase.table("user_avatars").insert(
                {"username": username, "avatar": DEFAULT_AVATAR}
            ).execute()
    except Exception:
        pass


def load_messages():
    try:
        response = supabase.table("messages").select("*").order("created_at").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading messages: {e}")
        return []


def save_message(username, content):
    try:
        supabase.table("messages").insert(
            {
                "username": username,
                "content": content,
                "created_at": datetime.now().isoformat(),
            }
        ).execute()
    except Exception as e:
        st.error(f"Error saving message: {e}")


def get_user_avatar(username):
    try:
        response = (
            supabase.table("user_avatars")
            .select("avatar")
            .eq("username", username)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]["avatar"]
    except Exception:
        pass
    return DEFAULT_AVATAR


def create_user_avatar(username, avatar):
    try:
        supabase.table("user_avatars").insert(
            {"username": username, "avatar": avatar}
        ).execute()
    except Exception as e:
        st.error(f"Error creating avatar: {e}")


def update_user_avatar(username, avatar):
    try:
        supabase.table("user_avatars").update({"avatar": avatar}).eq(
            "username", username
        ).execute()
    except Exception as e:
        try:
            supabase.table("user_avatars").insert(
                {"username": username, "avatar": avatar}
            ).execute()
        except Exception as e2:
            st.error(f"Error updating avatar: {e}")
            st.error(f"Error creating avatar: {e2}")


def get_all_user_avatars():
    try:
        response = supabase.table("user_avatars").select("username, avatar").execute()
        if response.data:
            return {item["username"]: item["avatar"] for item in response.data}
    except Exception:
        pass
    return {}


def chat():
    st.markdown(
        """<h2 class="chat-header"Group Chat/h2>""",
        unsafe_allow_html=True,
    )

    # Add this at the top of the file or near other UI components
    with st.sidebar:
        # Move "Logged in as" to the sidebar
        current_avatar = get_user_avatar(st.session_state.username)
        st.markdown(f"**Logged in as:** {current_avatar} @{st.session_state.username}")

        # Move "Set Pfp" and "Log Out" to the sidebar
        with st.expander("Settings"):
            if st.button("Set Pfp"):
                st.session_state.show_avatar_picker = True
                if st.session_state.get("show_avatar_picker", False):
                    st.markdown("### Select Your Avatar")

                    current_idx = 0
                    current_avatar = get_user_avatar(st.session_state.username)
                    if current_avatar in AVATAR_OPTIONS:
                        current_idx = AVATAR_OPTIONS.index(current_avatar)

                    selected = st.radio(
                        "Choose:",
                        AVATAR_OPTIONS,
                        index=current_idx,
                        horizontal=True,
                        label_visibility="collapsed",
                    )

                    col_confirm, col_cancel = st.columns([1, 1])
                    with col_confirm:
                        if st.button("**Confirm**"):
                            update_user_avatar(st.session_state.username, selected)
                            st.session_state.show_avatar_picker = False
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel"):
                            st.session_state.show_avatar_picker = False
                            st.rerun()
        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

    messages = load_messages()
    user_avatars = get_all_user_avatars()

    chat_container = st.container()
    with chat_container:
        for msg in messages:
            is_me = msg["username"] == st.session_state.username
            avatar = user_avatars.get(msg["username"], DEFAULT_AVATAR)
            timestamp = format_timestamp(msg["created_at"])
            with st.chat_message(f"@{msg['username']}", avatar=avatar):
                st.markdown(f"**@{msg['username']}:** {msg['content']}")
                st.caption(timestamp)

    st.divider()

    if prompt := st.chat_input("-> Type a message..."):
        save_message(st.session_state.username, prompt)
        st.rerun()


def main():
    if st.session_state.logged_in:
        chat()
    else:
        login()


if __name__ == "__main__":
    main()
