# Makefile for brewtils

PYTHON        = python
MODULE_NAME   = brewtils
TEST_DIR      = test
DOCKER_NAME    = bgio/plugins

VERSION        ?= 0.0.0

.PHONY: clean clean-build clean-docs clean-test clean-pyc docs help test

.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT
BROWSER := $(PYTHON) -c "$$BROWSER_PYSCRIPT"


# Misc
help:
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

install: clean ## install the package to the active Python's site-packages
	$(PYTHON) setup.py install


# Dependencies
deps: ## install python dependencies
	pip install -r requirements.txt


# Cleaning
clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-docs: ## remove doc artifacts
	rm -f docs/$(MODULE_NAME)*.rst
	rm -f docs/modules.rst

clean-python: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-sphinx: ## requires sphinx to be installed
	$(MAKE) -C docs clean

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

clean-all: clean-build clean-docs clean-python clean-sphinx clean-test ## remove everything

clean: clean-build clean-docs clean-python clean-test ## remove everything but sphinx


# Formatting
format: ## Run black formatter in-line
	black $(MODULE_NAME) $(TEST_DIR)


# Linting
lint: ## check style with flake8
	flake8 $(MODULE_NAME) $(TEST_DIR)
	black --check --diff $(MODULE_NAME) $(TEST_DIR)


# Testing / Coverage
test-python: ## run tests quickly with the default Python
	pytest $(TEST_DIR)

test-tox: ## run tests on every Python version with tox
	tox

test: test-python ## alias of test-python

coverage: ## check code coverage quickly with the default Python
	coverage run --source $(MODULE_NAME) -m pytest --tb=no
	coverage report -m
	coverage html

coverage-view: coverage ## view coverage report in a browser
	$(BROWSER) htmlcov/index.html

# Docker
docker-login: ## log in to the docker registry
	echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USER}" --password-stdin

docker-build-docs: docs
	docker build -t $(DOCKER_NAME):docs-$(VERSION) -f docs/Dockerfile docs/
	docker tag $(DOCKER_NAME):docs-$(VERSION) $(DOCKER_NAME):docs

docker-build:
	docker build -t $(DOCKER_NAME):python3-$(VERSION) --build-arg VERSION=$(VERSION) -f docker/python3/Dockerfile .
	docker build -t $(DOCKER_NAME):python3-onbuild-$(VERSION)  --build-arg VERSION=$(VERSION) -f docker/python3/onbuild/Dockerfile .
	docker build -t $(DOCKER_NAME):python2-$(VERSION) --build-arg VERSION=$(VERSION) -f docker/python2/Dockerfile .
	docker build -t $(DOCKER_NAME):python2-onbuild-$(VERSION) --build-arg VERSION=$(VERSION) -f docker/python2/onbuild/Dockerfile .
	docker tag $(DOCKER_NAME):python3-$(VERSION) $(DOCKER_NAME):latest
	docker tag $(DOCKER_NAME):python3-$(VERSION) $(DOCKER_NAME):python3
	docker tag $(DOCKER_NAME):python2-$(VERSION) $(DOCKER_NAME):python2


# Documentation
docs-deps: deps ## install dependencies for documentation
	pip install "sphinx~=6.2.1" sphinx_rtd_theme

docs: docs-deps ## generate Sphinx HTML documentation, including API docs
	sphinx-apidoc -o docs/ $(MODULE_NAME)
	$(MAKE) -C docs html

docs-view: docs ## view generated documenation in a browser
	$(BROWSER) docs/_build/html/index.html

docs-serve: docs ## generate the docs and watch for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .


# Packaging
package-source: ## builds source package
	$(PYTHON) setup.py sdist

package-wheel: ## builds wheel package
	$(PYTHON) setup.py bdist_wheel

package: clean package-source package-wheel ## builds source and wheel package
	ls -l dist


# Publishing
publish-package-test: package ## upload a package to the testpypi
	twine upload --repository testpypi dist/*

publish-package: package ## upload a package
	twine upload dist/*

publish-docker: docker-build ## push the docker images
	docker push $(DOCKER_NAME):python3-$(VERSION)
	docker push $(DOCKER_NAME):python3-onbuild-$(VERSION)
	docker push $(DOCKER_NAME):python2-$(VERSION)
	docker push $(DOCKER_NAME):python2-onbuild-$(VERSION)
	docker push $(DOCKER_NAME):latest
	docker push $(DOCKER_NAME):python3
	docker push $(DOCKER_NAME):python2

publish-docker-docs: docker-build-docs ## push the docker images
	docker push $(DOCKER_NAME):docs-$(VERSION)
	docker push $(DOCKER_NAME):docs
