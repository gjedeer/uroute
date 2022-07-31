"""Setup."""

from codecs import open
from os import path
from setuptools import setup, find_packages

from uroute.__version__ import VERSION

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file's "Overview" section
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    in_overview_section = False
    lines = []
    for line in f.read().split('\n'):
        if not in_overview_section and line.startswith('## Overview'):
            in_overview_section = True
            continue
        if in_overview_section:
            if line.startswith('##'):
                break
            lines.append(line)
    long_description = '\n'.join(lines).strip()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [
    x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')
]

setup(
    name='uroute',
    version=VERSION,
    description='Route URLs to configured browsers.',
    long_description=long_description,
    url='https://github.com/walterl/uroute',
    download_url='https://github.com/walterl/uroute/tarball/' + VERSION,
    license='LGPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        ('License :: OSI Approved :: '
         'GNU Lesser General Public License v3 (LGPLv3)'),
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Desktop Environment',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
    ],
    keywords='',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    author='Walter Leibbrandt',
    install_requires=install_requires,
    dependency_links=dependency_links,
    author_email='uroute wrl co za',
    entry_points={
        'console_scripts': [
            'uroute = uroute.__main__:main'
        ]
    }
)
