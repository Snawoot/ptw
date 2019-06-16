from setuptools import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='ptw',
      version='0.2.0',
      description='Pooling TLS Wrapper',
      url='https://github.com/Snawoot/ptw',
      author='Vladislav Yarmak',
      author_email='vladislav-ex-src@vm-0.com',
      license='MIT',
      packages=['ptw'],
      python_requires='>=3.5.3',
      setup_requires=[
          'wheel',
      ],
      install_requires=[
          'sdnotify>=0.3.2',
      ],
      extras_require={
          'uvloop': 'uvloop>=0.11.0',
          'dev': [
              'pytest>=3.0.0',
              'pytest-cov',
              'pytest-asyncio',
              'pytest-timeout',
              'pylint',
              'tox',
              'coverage',
              'async_generator',
              'setuptools>=38.6.0',
              'wheel>=0.31.0',
              'twine>=1.11.0',
              'cryptography>=1.6',
          ],
      },
      entry_points={
          'console_scripts': [
              'ptw=ptw.__main__:main',
          ],
      },
      classifiers=[
          "Programming Language :: Python :: 3.5",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Development Status :: 4 - Beta",
          "Environment :: No Input/Output (Daemon)",
          "Intended Audience :: System Administrators",
          "Natural Language :: English",
          "Topic :: Internet",
          "Topic :: Security",
      ],
      long_description=long_description,
      long_description_content_type='text/markdown',
      zip_safe=True)
