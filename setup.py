"""
Setup script for OmniAutomator
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="omni-automator",
    version="1.0.0",
    author="OmniAutomator Team",
    author_email="contact@omniautomator.com",
    description="Universal OS Automation Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/omniautomator/omni-automator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Desktop Environment",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "web": ["selenium>=4.15.0"],
        "dev": [
            # testing
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            # linting / formatting
            "ruff>=0.3.0",
            # type checking
            "mypy>=1.8.0",
            "types-requests",
            "types-PyYAML",
        ],
    },
    entry_points={
        "console_scripts": [
            "omni-automator=omni_automator.ui.cli:cli",
            "omni=omni_automator.ui.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
