import re

from setuptools import setup, find_packages


def find_version():
    version_file = "brewtils/__version__.py"
    version_line = open(version_file, "rt").read()
    match_object = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_line, re.M)

    if not match_object:
        raise RuntimeError("Unable to find version string in %s" % version_file)

    return match_object.group(1)


with open("README.rst") as readme_file:
    readme = readme_file.read()


setup(
    name="brewtils",
    version=find_version(),
    description="Beer-garden plugin and utility library",
    long_description=readme,
    url="https://beer-garden.io/",
    author="The Beer-garden Team",
    author_email=" ",
    license="MIT",
    packages=find_packages(exclude=["test", "test.*"]),
    package_data={"": ["README.md"]},
    install_requires=[
        "appdirs<2",
        "lark-parser<1",
        "marshmallow<4,>=3.3",
        "marshmallow-polyfield<6",
        "packaging",
        "pika<=1.4,>=1.0.1",
        "requests<3",
        "simplejson<4",
        "six<2",
        "wrapt",
        "yapconf>=0.3.7",
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
