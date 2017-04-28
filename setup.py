from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

with open('VERSION', encoding='utf-8') as f:
    package_version = f.read()

with open('requirements.txt', encoding='utf-8') as f:
    dependencies = []
    for line in f:
        line = line.strip()  # or someother preprocessing
        dependencies.append(line)

setup(
    name='alice-pooja',
    version=package_version,
    license='MIT',
    author='Pooja Shah',
    author_email='writeback2pooja@gmail.com',
    long_description=long_description,
    packages=find_packages(exclude=['build', 'dist']),
    url='https://github.com/moengage/alice',
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies
   )




