# PyYel-DevOps

The PyYel Development Operations extension. This repository regroups tools to simplify and speed up Python application back and front development process.

1. [Quick start](#quick-start) : how to install PyYel-CloudOps
1. [Content](#content)
    - [Logger](#logger) : Logging tool
    - [Setup](#setup) : Python project template
    - [Streamlit](#streamlit) : Pure Python front examples
    - [Wiki](#wiki) : Self-sufficient documentation generation and hosting
1. [Notes](#notes)

## Quick start

**Note:** _In most cases,_ PyYel-DevOps _modules should be copied into your project to serve as a working base for further developments, as all the modules are not designed to be imported as Python packages._

1. Clone the repository and Install the library.

``` bash
(your_env) your_path/PyYel-DevOps> pip install .
```

2. Import the library into you code.

``` python
import pyldev
```

3. Import the relevant features.

``` python
from pyldev.logger import LoggerPrintIntercept
```


## Content

The content of *pyldev*. Unless specified diferently, all the modules may be directly imported into Python code as libraries.

### Logger

|Module|Description|
|------|-----------|
|LoggerPrintIntercept|A standard logger that will intercept ``print()`` statement to log them as DEBUG verbose|

### Setup
A non-Python library. This module should not be imported into Python scripts.

Offers tools to quick-start a new development project.

### Streamlit
A collection of predefined Streamlit frontend models. Although importable, most use case will require to redifine the pages layout to better fit the desired application design.

It is thus recommend to rather copy-paste wished the parent and children templates and then customize it from within you own code.


### Wiki
A non-Python library. This module should not be imported into Python scripts.

Offers tools to help building compatible and sustainable documentation for a project.

|Module|Purpose|
|--------------|----|
|Raw|To create raw documentation as markdowns|
|Mkdocs|To convert raw documentation into Mkdocs format and host it locally|
|Gitlab|To convert raw documentation into Gitlab format|

See the ``.bat`` files and the module [README](./pyldev/wiki/README.md) to use the wiki tools. 

## Note

See also [***PyYel-MLOps***](https://github.com/PyYel/PyYel-MLOps) and [***PyYel-CloudOps***](https://github.com/PyYel/PyYel-CloudOps) for AI and deployment tools.