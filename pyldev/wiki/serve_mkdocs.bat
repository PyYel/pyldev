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
python wiki_to_docs.py

:: Install mkdocs and mkdocs-material if not already installed
echo Installing mkdocs and mkdocs-material...
pip install mkdocs mkdocs-material --quiet

:: Build the MkDocs site
echo Building the MkDocs site...
mkdocs build

:: Serve the MkDocs site locally
echo Serving the MkDocs site locally...
mkdocs serve

echo Files from /wiki converted and moved to /docs. An error seem to have appeared when serving the local server: see the exception above.

pause
