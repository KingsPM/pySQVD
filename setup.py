from setuptools import setup

setup(name='pysqvd',
  version='1.2.6',
  description='Python API library for SQVD',
  url='http://github.com/preciserobot/sqvd',
  author='David Brawand',
  author_email='dbrawand@nhs.net',
  license='Apache 2.0',
  packages=['pysqvd'],
  install_requires=[
    "requests",
    "six"
  ],
  zip_safe=False)
