import re

from setuptools import setup, find_packages


def find_version():
    version_file = "brewtils/_version.py"
    version_line = open(version_file, "rt").read()
    match_object = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_line, re.M)

    if not match_object:
        raise RuntimeError("Unable to find version string in %s" % version_file)

    return match_object.group(1)


setup(
    name='brewtils',
    version=find_version(),
    description='Utilities for building and running beer-garden Systems',
    url=' ',
    author='The beer-garden Team',
    author_email=' ',
    license='MIT',
    packages=find_packages(exclude=['test', 'test.*']),
    package_data={'': ['README.md']},
    install_requires=[
        'marshmallow',
        'pika',
        'requests',
        'six',
        'wrapt',
        'lark-parser',
        'enum34;python_version<"3.4"',
        'futures;python_version<"3.0"'
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
