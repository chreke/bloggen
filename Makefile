.PHONY: install all

all:
	python generate.py

install: dev-requirements.txt requirements.txt
	pip-sync requirements.txt dev-requirements.txt

dev-requirements.txt: dev-requirements.in requirements.txt
	pip-compile dev-requirements.in

requirements.txt: requirements.in
	pip-compile requirements.in
