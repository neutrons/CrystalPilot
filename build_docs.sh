SPHINX_APIDOC_OPTIONS=members,show-inheritance sphinx-apidoc -o docs/source src
sphinx-build -M html docs docs/_build
