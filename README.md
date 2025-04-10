# dataset-profiler

Repository of the dataset-profiler DataGEMS service


## Getting started with your project

### 1. Clone the repository

```bash
git clone git@github.com:datagems-eosc/dataset-profiler.git
```

### 2. Set Up Your Development Environment

If you do not have `uv` installed, you can install it with

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
After executing the command above, you will need to restart your shell.

`uv` is a python package similar to `poetry`.

Then, install the environment and the pre-commit hooks with

```bash
make install
```

This will also generate your `uv.lock` file
