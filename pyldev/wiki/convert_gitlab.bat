@echo off

:: Converting the wiki to the mkdocs format
python raw_to_gitlab.py

echo Files from /raw converted and moved to /gitlab. You may now close the terminal.

pause