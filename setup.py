from setuptools import setup, find_packages

setup(
    name="moderntensor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "cryptography>=3.4.0",
        "pycardano>=0.7.0",
        "aptos-sdk>=0.10.0",
        "python-dotenv>=0.19.0",
        "rich>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "aptosctl=mt_aptos.cli.main:aptosctl",
        ],
    },
    author="ModernTensor",
    author_email="your.email@example.com",
    description="A command line interface for managing Aptos accounts and operations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/moderntensor",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
) 