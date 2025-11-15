from setuptools import setup, find_packages

setup(
    name="linear-initiative-filter-view",
    version="0.1.0",
    description="Automatically updates Initiative views in Linear with custom filters",
    author="",
    packages=find_packages(),
    install_requires=[
        "gql[all]>=3.5.0",
        "click>=8.1.0",
        "tomli>=2.0.0;python_version<'3.11'",
        "pyparsing>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "linear-filter=linear_filter.cli:main",
        ],
    },
    python_requires=">=3.9",
)
