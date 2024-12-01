# PyYel-DevOps

The PyYel Development Operations extension. This repository regroups tools to simplify and speed up Python application back and front development process.

## Quick start
1. Clone the repository and Install the library.

``` bash
your_path/PyYel-DevOps> pip install .
```

2. Import the library into you code.

``` python
import pyldev
```

3. Import the relevant features.

``` python
from pyldev.streamlit import StreamlitHome
```

## Content

The content of pyldev. Unless specified diferently, all the modules may be directly imported into Python code as libraries.

### Streamlit
A collection of predefined Streamlit frontend models. Although importable, most use case will require to redifine the pages layout to better fit the desired application design.

It is thus recommend to rather copy-paste wished the parent and children templates and then customize it from within you own code.

|PyYel Template|Purpose|Status|
|--------------|----|------|
|Streamlit|An abstract class to serve as a model|Done|
|StreamlitChatbot|A multi-purpose chatbot page, that seemingly integrates with backend API calls|WIP|
|StreamlitHome|A basic homepage to welcome the user and introduce it to the navigation|WIP|

### Setup
A non-Python library. This module should not be imported into Python scripts.

Offers tools to quick-start a new development project.

### Wiki
A non-Python library. This module should not be imported into Python scripts.

Offers tools to help building compatible and sustainable documentation for a project.

|Source|Purpose|Status|
|--------------|----|------|
|Raw|To create raw documentation as markdowns|Done|
|Mkdocs|To convert raw documentation into Mkdocs format and host it locally|Done|
|Gitlab|To convert raw documentation into Gitlab format|Done|

See the ``.bat`` files and the module [README](./pyldev/wiki/README.md) to use the wiki tools. 

## Note

See also ***PyYel-MLOps*** and ***PyYel-CloudOps*** for AI and deployment tools.