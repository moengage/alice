from setuptools import setup

setup(
    name='aliceGithubWebhook',
    version='1.0',
    long_description=__doc__,
    packages=['alice'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask']
)
