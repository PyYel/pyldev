@echo off

echo Building the python-base image...
cd ..

docker build -f "python-base.dockerfile" -t "python-base:latest" .

echo Program completed. You may close this terminal. If an error araised, see the exception above.

pause