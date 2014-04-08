from distutils.core import setup

setup(
    name='django-subtyping',
    version='0.1-dev',
    test_suite='subtyping.test',
    packages=['subtyping'],
    install_requires=[],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.rst').read(),
)
