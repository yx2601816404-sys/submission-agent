from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="submission-agent",
    version="2.1.0",
    description="投稿代理 — 帮助中国创作者找到最合适的国际文学竞赛",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Submission Agent",
    license="MIT",
    python_requires=">=3.8",
    py_modules=["cli", "matcher", "refresher", "profiles", "tracker", "translator"],
    package_data={"": ["competitions.json"]},
    data_files=[("", ["competitions.json"])],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "submission-agent=cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Linguistic",
    ],
)
