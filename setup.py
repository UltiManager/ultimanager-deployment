from setuptools import setup, find_packages

setup(
    # Package meta-data
    name="ultideploy",
    version="0.0.0",
    description="Python package to manage deploying UltiManager.",
    author="UltiManager",
    author_email="team@ultimanager.com",
    url="https://github.com/UltiManager/ultimanager-deployment",
    license="MIT",
    # Include the actual source code
    include_package_data=True,
    packages=find_packages(),
    # CLI Entry Point
    entry_points={
        'console_scripts': ['ultideploy=ultideploy.cli:main']
    },
    # Dependencies
    install_requires=[
        "google-api-python-client",
        "google-cloud-resource-manager",
        "oauth2client"
    ],
)
