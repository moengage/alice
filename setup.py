from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = f.read()

with open('VERSION') as f:
    package_version = f.read()

with open('requirements.txt') as f:
    dependencies = []
    for line in f:
        line = line.strip()
        dependencies.append(line)

setup(
    name='alice-core',
    version=package_version,
    license='MIT',
    long_description=long_description,
    author_email='writeback2pooja@gmail.com',
    author='Pooja Shah',
    packages=find_packages(exclude=['build', 'dist']),
    url='https://github.com/moengage/alice',
    include_package_data=True,
    zip_safe=False,
    # package_data={'': ['VERSION', 'changes.md']},
    install_requires=dependencies
   )
