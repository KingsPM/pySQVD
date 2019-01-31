from setuptools import setup

setup(name='pysqvd',
  version='1.0.0',
  description='Python convenience API for SQVD',
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

