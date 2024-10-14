from setuptools import setup

setup(
    name="cross-project-cluck",              
    version="1.0.0",                 
    py_modules=["cross-project-cluck"],
    description="CLI tool to identify cross project repo access in Azure DevOps.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="ytimyno",
    author_email="ytimyno@gmail.com",  # Your email
    url="https://github.com/ytimyno/cross-project-cluck",  # Project URL (optional)
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",  # License classifier
        "Operating System :: OS Independent",
    ],
    license="GPLv3",
    entry_points={
        'console_scripts': [
            'cluck=cross_project_cluck:main',  # Command-line entry point
        ],
    },
    python_requires='>=3.6',         # Minimum Python version
)