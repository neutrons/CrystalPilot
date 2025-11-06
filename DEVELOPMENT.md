# Development Guide

This document provides guidelines and instructions for setting up and contributing to
the CrystalPilot project.

## Starting from the template

- Add other Python dependencies you project need with [`pixi add`](https://pixi.sh/dev/reference/cli/pixi/add/).
- Modify Dockerfile as needed. Please make sure it can still run as non-root (we use it in GitLab CI/CD and in general this
is a good practice).
- install pre-commit (if not already installed) - `pip install pre-commit`
- activate `pre-commit` for your project: `cd <project folder> && pre-commit install`
- finally, clear the content of this section and add the description of your project. You can keep/adjust instructions
below

Note 1: please don't change linter settings, license, code of conduct without discussing with the team first - we want to keep them
the same for all our projects.

Note 2: if you think some changes that you've made might be useful for other projects as well, please fill free
to create an issue [in this repo](https://code.ornl.gov/ndip/project-templates/python/-/issues/new)


## Installation
Start by installing [Pixi](https://pixi.sh/latest/). Once done, run the following:

```commandline
pixi install
```

## Running
### From source
```bash
pixi run app
```

### Using Docker
```bash
# build from source
docker build -f dockerfiles/Dockerfile -t exphub .
# run a container
docker run -p 8081:8081 -e EP_PATH=/app exphub
```

Your application will now be running at http://localhost:8081/app.

## Formatting
```commandline
pixi run ruff format
```

## Linting
```commandline
pixi run ruff check
pixi run mypy .
```

## Testing
```commandline
pixi run pytest
```
or, with coverage
```commandline
pixi run coverage run
pixi run coverage report
```

## Updating project from template

This project was created from a [template](https://code.ornl.gov/ndip/project-templates/nova-application-template.git) using [copier](https://copier.readthedocs.io/). If the template has changed, you
can try to update the project to incorporate these changes. Just enter the project folder, make sure `git status`
shows it clean, and run:
```
copier update
```
See [here](https://copier.readthedocs.io/en/stable/updating/#updating-a-project) for more information.


## CI/CD in GitLab

Take a look at the [`.gitlab-ci.yml`](.gitlab-ci.yml) file. It configures pipelines to run in GitLab.
Some jobs will run automatically on each commit, jobs to
build packages and Docker images need to be triggered manually.


### Versioning

The "source of truth" for the version number is in the [`pyproject.toml`](pyproject.toml) file. It is used for Docker
image tags, python package versioning, and automatic creation of git tags.

### Documentation for calvera.ornl.gov/docs

Please create a User Guide for CrystalPilot and we can add it to our
[site](https://calvera.ornl.gov/docs/user_guide/tools). The documentation is a standard markdown and should
 be located in _docs/web/docs_ folder. We have already created some files there that give you an idea how it could look like. Please
 modify as needed.

 You can also build your guide locally:

 Please make sure you have Node.js [installed](https://nodejs.org/en/download).

 Then:

```bash
cd docs/web
npm install
npm run start
```

the documentation will be compiled and available at http://localhost:3000/. If you keep the server running, it will update the
site as you modify the documents.
