import streamlit as st
import os, sys
import hashlib
from constants import MAIN_DIR, ASSETS_DIR, TMP_DIR
from uuid import uuid4
import webbrowser

from .Page import Page


class PageLogin(Page):
    """
    Parent frontend class
    """

    def __init__(self):
        super().__init__()

    def _load_page(self):

        # st.image(os.path.join(ASSETS_DIR, "my_asset.png"), use_container_width=True)
        st.write("")
        with st.form(key="login", border=False):

            st.title("My App Login")

            api_token = st.text_input("My App API token", max_chars=40)

            submit_button = st.form_submit_button(
                label="Login", type="primary", use_container_width=True
            )
            if submit_button:
                if len(api_token) == 40 and api_token != "":

                    # API token is loaded and accessed from the session uuid
                    st.session_state.api_token = api_token
                    st.session_state.uuid = uuid4()
                    st.session_state[st.session_state.uuid] = api_token

                    # user_hash is the user's session, created from hashing its login key
                    st.session_state["user_hash"] = self._hash_api_token()
                    self._create_user_session()  # Creates session id first time login

                    # Loads homepage with saved API credentials
                    st.success(f"Login in as: {api_token}")
                    st.session_state.page = "Home"
                    st.rerun()

                elif len(api_token) == 0:
                    st.error(f"Enter an API key to log in")

                else:
                    st.error(f"Invalid API key: {api_token}")

        st.markdown(
            """
            <style>
            .button-container {
                display: flex;
                justify-content: flex-start;
            }
            .button-container > div {
                margin-right: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st._bottom:
            st.markdown('<div class="button-container">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 8, 2])
            with col1:
                if st.button(label=":grey_question:", help="About my data"):
                    st.session_state.page = "About"
                    st.rerun()
            with col3:
                st.markdown(
                    f"[Check out PyYel!](https://github.com/PyYel/PyYel-DevOps/)",
                    unsafe_allow_html=True,
                )

    def _create_user_session(self):
        """
        In the event of a first time login, creates new entry in the user's database, i.e.,
        adds hashed folder in the data folder to host user's workspace and conversation data.
        """

        os.makedirs(
            os.path.join(MAIN_DIR, "data", "user", st.session_state["user_hash"]),
            exist_ok=True,
        )

        return None

    def _hash_api_token(self):
        """
        Hashes the current api_token into a unique readable sha256 key.
        """
        api_key_bytes = st.session_state.api_token.encode("utf-8")

        sha256_hash = hashlib.sha256()
        sha256_hash.update(api_key_bytes)

        return sha256_hash.hexdigest()
