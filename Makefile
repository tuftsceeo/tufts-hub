clean:
	rm -rf build dist *.egg-info
	rm -rf .coverage
	rm -rf .pytest_cache
	rm -rf docs/docs
	rm -rf docs/site
	find . | grep -E "(__pycache__)" | xargs rm -rf

tidy:
	black -l 79 src/thub/*.py
	black -l 79 tests/*.py

test:
	pytest --cov=src/thub --cov-report=term-missing

check: clean tidy test

dist: check
	python3 -m build

publish: dist
	twine upload --sign dist/*
