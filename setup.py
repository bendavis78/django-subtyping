from distutils.core import setup

setup(
    name='django-generic-helpers',
    version='0.1-dev',
    test_suite='generic_helpers.test',
    packages=['generic_helpers'],
    install_requires=[],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.rst').read(),
)
