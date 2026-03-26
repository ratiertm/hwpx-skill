#!/usr/bin/env python3
"""setup.py for cli-anything-hwpx

Install with: pip install -e .
"""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-hwpx",
    version="1.0.0",
    author="cli-anything contributors",
    description="CLI harness for HWPX documents - Read, edit, and create Hancom Office HWPX files via command line",
    long_description=open("cli_anything/hwpx/README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/HKUDS/CLI-Anything",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Office Suites",
        "Topic :: Text Processing :: Markup :: XML",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "python-hwpx>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-hwpx=cli_anything.hwpx.hwpx_cli:main",
        ],
    },
    package_data={
        "cli_anything.hwpx": ["skills/*.md"],
    },
    include_package_data=True,
    zip_safe=False,
)
