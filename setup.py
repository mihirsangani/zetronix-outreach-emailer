from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zetronix-outreach-emailer",
    version="1.0.0",
    author="Zetronix",
    description="AI-powered outreach email generator with Google Sheets integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Business",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "google-api-python-client>=2.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=1.0.0",
        "gspread>=5.0.0",
        "oauth2client>=4.1.3",
        "python-dotenv>=1.0.0",
        "jinja2>=3.1.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
    ],
    entry_points={
        "console_scripts": [
            "zetronix-emailer=zetronix_emailer.cli:main",
        ],
    },
)