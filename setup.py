from setuptools import setup, find_packages

setup(
    name="cross-project-cluck",              
    version="1.0.0",                 
    description="CLI tool to identify cross project repo access in Azure DevOps.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="ytimyno",
    author_email="ytimyno@gmail.com",
    url="https://github.com/ytimyno/cross-project-cluck",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    license="GPLv3",
    packages=find_packages()
)