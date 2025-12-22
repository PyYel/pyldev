import os, sys
import time
import streamlit as st
from threading import Thread
from streamlit import delta_generator

from .page import *
from constants import ASSETS_DIR


class Front:
    """
    Frontend main thread as a class.
    """

    def __init__(self):
        super().__init__()

        st.set_page_config(
            page_title="My App", page_icon=os.path.join(ASSETS_DIR, "icon.ico")
        )

        # Render the selected page
        if st.session_state.page == "Login":
            page_login = PageLogin()
            page_login._load_page()
        elif st.session_state.page == "About":
            page_about = PageAbout()
            page_about._load_page()
