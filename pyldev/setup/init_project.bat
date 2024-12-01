@echo off
:: Create main project directory
set PROJECT_NAME=my-python-app
mkdir %PROJECT_NAME%

:: Navigate into the project directory
cd %PROJECT_NAME%

:: Create main directories
mkdir bin lib src tests docs configs scripts .github\workflows

:: Create src/app directory and __init__.py
mkdir src\app
echo. > src\app\__init__.py
echo # Main application entry point > src\app\main.py
echo # Utility functions or helpers > src\app\utils.py
echo # Configuration settings > src\app\config.py

:: Create test files
echo # Tests for the main application > tests\test_main.py
echo # Tests for utility functions > tests\test_utils.py

:: Create config files
echo # Development configuration > configs\dev.yaml
echo # Staging configuration > configs\staging.yaml
echo # Production configuration > configs\prod.yaml

:: Create scripts
echo #!/bin/bash > scripts\deploy.sh
echo #!/bin/bash > scripts\setup_env.sh

:: Create .github/workflows
echo # GitHub CI workflow > .github\workflows\ci.yml

:: Create core files
echo # Python dependencies > requirements.txt
echo # Project metadata and build configuration > pyproject.toml
echo # Packaging configuration > setup.py
echo # Project overview and instructions > README.md
echo # License for the project > LICENSE
echo # Environment variables > .env

echo Folder structure created successfully!
pause
