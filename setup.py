"""Setup script for legal texts processing project"""
from setuptools import setup, find_packages

setup(
    name="law-texts-processing",
    version="0.1.0",
    description="Обработка и систематизация юридических текстов с помощью онтологий",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "rdflib>=6.3.1",
        "pandas>=2.1.4",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "nltk>=3.8.1",
        "spacy>=3.7.2",
        "pymorphy2>=0.9.1",
        "beautifulsoup4>=4.12.2",
        "lxml>=4.9.3",
        "SPARQLWrapper>=2.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
    ],
    python_requires=">=3.8",
)

