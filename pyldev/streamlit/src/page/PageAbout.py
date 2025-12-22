import streamlit as st
import os, sys

from constants import MAIN_DIR, ASSETS_DIR

from .Page import Page


class PageAbout(Page):
    """
    Parent frontend class
    """

    def __init__(self):
        super().__init__()

    def _load_page(self):

        st.title("About My App")
        st.caption("My app subtitle")

        st.subheader("What Happens to My Data")
        st.markdown(
            """
            Your data is definitely safe.
            """
        )

        with st._bottom:
            if st.button("Back to homepage", type="primary", use_container_width=True):
                st.session_state.page = "Login"
                st.rerun()
