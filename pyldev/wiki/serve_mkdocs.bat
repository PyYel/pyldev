@echo off

:: Converting the wiki to the mkdocs format
echo 1/5 Converting raw markdown to mkdocs format...
python raw_to_docs.py

:: Install mkdocs and mkdocs-material if not already installed
echo 2/5 Installing mkdocs and mkdocs-material...
pip install mkdocs mkdocs-material --quiet

:: Build the MkDocs site
echo 3/5 Building the mkdocs site...
mkdocs build >nul 2>&1

:: Serve the MkDocs site locally
echo 4/5 Serving the mkdocs site locally...
@REM mkdocs serve >nul 2>&1
start /B "" cmd /c "mkdocs serve >nul 2>&1"

echo 5/5 mkdocs server up locally http://127.0.0.1:8000/ ...

