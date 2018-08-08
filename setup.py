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
    url='https://beer-garden.io/',
    author='The beer-garden Team',
    author_email=' ',
    license='MIT',
    packages=find_packages(exclude=['test', 'test.*']),
    package_data={'': ['README.md']},
    install_requires=[
        'lark-parser<0.7',
        'marshmallow<3',
        'marshmallow-polyfield<4',
        'pika<0.13',
        'pyjwt<2',
        'requests<3',
        'simplejson<4',
        'six<2',
        'wrapt<2',
        'yapconf>=0.2.1',
    ],
    extras_require={
        ':python_version=="2.7"': ['futures',],
        ':python_version<"3.4"': ['enum34',]
    },
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
