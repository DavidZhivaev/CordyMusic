from setuptools import setup, find_packages

setup(
    name="CordyMusic",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    python_requires='>=3.8',
    description="Discord bot for streaming and managing music from Yandex Music, Spotify, and SoundCloud",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="DavidZhivaev",
    url="https://github.com/DavidZhivaev/CordyMusic/",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
