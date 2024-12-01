# PyYel DevOps: Wiki

A collection of utils to create and host documentation.

## Create a wiki

Create a wiki in the ``/wiki`` folder. This should be markdown only, and the files must respect the wiki hierarchy:
- A markdown is a wiki page
- The folder hierarchy will define the wiki urls hierarchy
- A good practice shoud be to have a page for every eponymous folder

``` bash
# In the /wiki folder:
wiki
├── _sidebar.md                     # For custom sidebar on gitlab and mkdocs
├── assets/                         # Folder containing images, diagrams, etc.
│   ├── logo.png                    # Project logo or branding
│   ├── architecture_diagram.png    # System architecture diagram
│   └── example_config.yaml         # Example configuration file
├── home.md                         # The first page of your wiki, will most likely be a link page
└── home/                           # The folder to start from
    ├── about_the_data.md           # A page not complex enough to be broken down into subpages
    └── about_the_features.md       # A page complex enough to be broken down into subpages
    └── about_the_features/
        ├── feature_1.md            # To detail my feature 1
        └── feature_1.md            # To detail my feature 2
```

You may copy the /pyldev/wiki repository to your project, but it is recommended to keep the folder structure identical to ensure the reliability of the QoL programs hat come with it.

## Host on Gitlab
When creating a wiki on Gitlab, the webpages naming is changed:
- A page named: ``wiki/home/my_page.md``
- Must be converted to: ``url/wiki/home/mypage``

The ``wiki_to_lab.py`` script helps this conversion by editing the relative paths found in your wiki page, so the title and links keep working. The content of the ``/lab`` folder should be then copy pasted to you ``repo.wiki`` folder.

## Host locally using Mkdocs
When creating a wiki using Mkdocs, the pages are converted to html:
- A page named: ``wiki/home/my_page.md``
- Must be converted to: ``localhost/wiki/home/my_page/index.html``

The ``wiki_to_docs.py`` script helps this conversion by editing the relative paths found in your wiki page, so the title and links keep working. The content of the ``/docs`` folder are then build into ``/site`` by the ``mkdocs.exe`` file. You may use ``serve.bat`` to host the 
