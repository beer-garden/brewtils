import re

from setuptools import setup, find_packages


def find_version():
    version_file = "brewtils/__version__.py"
    version_line = open(version_file, "rt").read()
    match_object = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_line, re.M)

    if not match_object:
        raise RuntimeError("Unable to find version string in %s" % version_file)

    return match_object.group(1)


with open("README.md") as readme_file:
    readme = readme_file.read()


setup(
    name="brewtils",
    version=find_version(),
    description="Beer-garden plugin and utility library",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://beer-garden.io/",
    author="The Beer-garden Team",
    author_email=" ",
    license="MIT",
    packages=find_packages(exclude=["test", "test.*"]),
    package_data={"": ["README.md"]},
    install_requires=[
        "appdirs<2", # Latest 1.4.4
        "lark-parser<1", # Latest 0.12.0
        "marshmallow<4.1,>=4.0", # Latest 4.0.1
        "packaging", # Latest 25.0
        "pika<=1.4,>=1.0.1", # Latest 1.3.2
        "requests<3", # Latest 2.32.5
        "simplejson<4", # Latest 3.20.2
        "wrapt", # Latest 1.17.3
        "yapconf<0.5,>=0.3.7", # Latest 0.5.0
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
