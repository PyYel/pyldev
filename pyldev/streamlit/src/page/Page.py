from abc import abstractmethod, ABC
import os, sys
import time
import streamlit as st
from streamlit import delta_generator
from threading import Thread


class Page(ABC):
    """
    Parent frontend class
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _load_page(self):
        pass

    def update_progress_bar(
        self,
        path: str,
        progress_bar: delta_generator,
        watched_thread: Thread,
        progress_bar_name: str = None,
    ):
        """
        Reads a txt file and updates a progress bar. The file must be of format 'action_name, progress_float'.
        """

        if progress_bar_name is None:
            progress_bar_name = watched_thread.name

        # Init
        with open(path, "r") as f:
            progress_percentage = float(f.read())
        progress_bar.progress(progress_percentage)

        # While process in is in progress
        while progress_percentage < 1:  # and watched_thread.is_alive():
            time.sleep(0.1)
            try:
                with open(path, "r") as f:
                    progress_percentage = float(f.read())
                progress_percentage = min(progress_percentage, 1.0)
                progress_bar.progress(progress_percentage, progress_bar_name)

                if (progress_percentage < 1) and not watched_thread.is_alive():
                    print(
                        f"Thread {watched_thread.getName()} died while progess percentage was at {round(progress_percentage, 3)}"
                    )
                    break
            except:
                None

        # Progress reset once done
        with open(path, "w") as f:
            f.write("0")

        return None
