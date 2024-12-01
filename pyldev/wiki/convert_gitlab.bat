@echo off
:: Check if .venv exists
IF NOT EXIST .venv (
    echo No virtual environment found. Creating .venv...
    python -m venv .venv
    echo Virtual environment .venv created.
)

:: Activate the virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate

:: Converting the wiki to the mkdocs format
python wiki_to_lab.py

echo Files from /wiki converted and moved to /lab. You may now close the terminal.

pause