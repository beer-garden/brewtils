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
        "lark-parser<0.7",
        "marshmallow<3",
        "marshmallow-polyfield<4",
        "packaging<21",
        "pika<=1.1,>=0.11",
        "pyjwt<2",
        "pytz<2021",
        "requests<3",
        "simplejson<4",
        "six<2",
        "wrapt<2",
        "yapconf>=0.3.7",
    ],
    extras_require={
        ':python_version=="2.7"': ["futures", "funcsigs"],
        ':python_version<"3.4"': ["enum34"],
        ':python_version<"3.5"': ["typing"],
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
