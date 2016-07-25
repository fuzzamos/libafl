from distutils.core import setup

with open('README.md') as file:
    readme = file.read()

setup(
    name = 'libafl',
    packages = ['libafl'],
    version = '0.0.1',
    description = 'A library for using AFL from python',
    long_description=readme,
    author = 'Gulshan Singh',
    author_email = 'gsingh2011@gmail.com',
    url = 'https://github.com/gsingh93/libafl',
    download_url = 'https://github.com/gsingh93/libafl/tarball/master',
    keywords = ['afl', 'fuzz'],
    classifiers = [],
)
