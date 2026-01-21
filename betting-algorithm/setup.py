from setuptools import setup, find_packages

setup(
    name='betting-algorithm',
    version='2.0.0',
    packages=find_packages(),
    install_requires=[
        'pandas>=1.5.0',
        'numpy>=1.23.0',
        'requests>=2.28.0',
    ],
    author='Your Name',
    description='Professional Sports Betting Algorithm',
    python_requires='>=3.8',
)
