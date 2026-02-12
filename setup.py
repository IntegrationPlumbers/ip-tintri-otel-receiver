"""Setup configuration for Tintri OpenTelemetry Receiver."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tintri-otel-receiver",
    version="1.0.0",
    author="Integration Plumbers",
    author_email="support@integrationplumbers.io",
    description="OpenTelemetry Collector Receiver for Tintri storage infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IntegrationPlumbers/ip-tintri-otel-receiver",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "requests>=2.31.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.2",
        "typing-extensions>=4.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
            "pytest-asyncio>=0.21.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
            "types-requests>=2.31.0",
            "types-PyYAML>=6.0.12",
        ],
    },
    entry_points={
        "console_scripts": [
            "tintri-receiver=tintri_receiver.cli:main",
        ],
    },
)
