#!/usr/bin/env python
from setuptools import setup, find_packages


install_requires = [
    'waldur-core>=0.151.0',
    'waldur-freeipa>=0.2.4',
]


tests_requires = [
    'ddt>=1.0.0,<1.1.0',
    'factory_boy==2.4.1',
    'freezegun==0.3.7',
    'mock>=1.0.1',
    'mock-django==0.6.9',
    'six>=1.9.0',
    'sqlalchemy>=1.0.12',
]


setup(
    name='waldur-slurm',
    version='0.5.0',
    author='OpenNode Team',
    author_email='info@opennodecloud.com',
    url='http://waldur.com',
    description='Waldur plugin for SLURM accounting synchronization.',
    long_description=open('README.rst').read(),
    license='MIT',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=install_requires,
    extras_require={
        'tests': tests_requires,
    },
    zip_safe=False,
    entry_points={
        'waldur_extensions': (
            'waldur_slurm = waldur_slurm.extension:SlurmExtension',
        ),
    },
    include_package_data=True,
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
)
