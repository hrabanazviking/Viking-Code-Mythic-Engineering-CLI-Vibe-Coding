# Clean Code in Python (with examples)

[Clean Code](https://www.google.de/books/edition/Clean_Code/_i6bDeoCQzsC?hl=en&gbpv=0) by Robert C. Martin, is a
handbook for software developers that introduces design principles and ideas for clean code.

This repository focuses on the principles introduced in the book, with a focus on Python. It goes hand in hand with the
"Clean up your code" workshop, for which you can find the slides [here](slides/).

## Prerequisites

To be able to run the code in this repository, you will need to have the following two prerequisites fulfilled:

### 1. Python version of at least 3.9

You will need to have Python version of at least 3.9 installed.

Here are a few useful tools that let you manage multiple Python installations on your machine:

- [pyenv](https://github.com/pyenv/pyenv): easy to use, reliable, and integrates well with most package manager tools.
- [conda](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html) or
  [miniconda](https://docs.anaconda.com/miniconda/).
- [asdf](https://github.com/asdf-community/asdf-python) similar to `pyenv` but more versatile because it can manage
  other programming languages as well.

### 2. Poetry installed

You will need to have [Poetry](https://python-poetry.org/) of at least version 1.8.0 to be able to install the
package dependencies listed in the [poetry.lock](poetry.lock) file.

To install Poetry, check out the [installation guide](https://python-poetry.org/docs/#installing-with-the-official-installer)
or simply run the following command on your Linux, Mac or Windows machine:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

## Installation

> :exclamation: **Disclaimer:** The installation was tested only on Mac and Linux machines.

1. Clone the repository:

   ```bash
   git clone https://github.com/pythonmonty/clean-code-in-python.git
   ```

2. Navigate into the directory (if not already):

   ```bash
   cd clean-code-in-python
   ```

3. [Optional] Set Poetry to create the virtual environment in-project.

   ```bash
   poetry config virtualenvs.in-project true
   ```

4. Set a Python version for your Poetry environment. The Python version should be 3.9. or higher.
   If you are using `pyenv` to manage your Python versions, you can install a specific Python version,
   set it as the local version of the directory and configure Poetry to use it.

   ```bash
   pyenv install 3.11.8
   pyenv local 3.11.8
   poetry env use $(pyenv which python)
   ```

   > :memo: **Note:** As an example I picked Python 3.11.8, but if you cannot install that particular version on
   > your machine, you can check which Python 3.11 versions are available by running `pyenv install --list | grep 3.11`.

   Alternatively, you can explicitly tell Poetry which Python version to use by passing the path to the Python
   executable:

   ```bash
   poetry env use /full/path/to/python
   ```

5. [Optional] To check if your Python executable has been set correctly, you can run:

   ```bash
   poetry env info
   ```

6. Install the package dependencies and activate the environment:

   ```bash
   poetry install
   poetry shell
   ```

## Repository structure

The repository has the following structure:

- [exercises](exercises): Contains Python exercises, divided into:
  - [exercises/classes](exercises/classes): exercises regarding clean classes,
  - [exercises/functions](exercises/functions): exercises regarding clean functions.
- [slides](slides): Contain PDF slides that were presented during the tutorial.
- [pyproject.toml](pyproject.toml): Poetry dependencies, ruff and mypy configurations.
- [poetry.lock](poetry.lock): Poetry lock file where all package dependencies are locked and hashed.
