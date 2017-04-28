from setuptools import setup, find_packages

setup(
    name='alice-pooja',
    version='1.0',
    py_modules= '',
    author='Pooja Shah',
    author_email='writeback2pooja@gmail.com',
    #long_description=__doc__,
    long_description=open('README').read(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Flask==0.13.dev0',
        'slacker==0.9.24',
        'python-jenkins==0.4.13'])

