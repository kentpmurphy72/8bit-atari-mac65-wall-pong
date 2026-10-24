ATASM ?= .tools/src/atasm
PYTHON ?= .venv/bin/python

.PHONY: all bootstrap test mac65 clean
all: build/wall-pong.xex

bootstrap:
	./tools/bootstrap-atasm.sh
	python3 -m venv .venv
	.venv/bin/python -m pip install -r tests/requirements.txt

build/wall-pong.xex build/labels.txt &: src/wallpong.m65
	mkdir -p build
	$(ATASM) -obuild/wall-pong.xex -lbuild/labels.txt $<

test: all build/labels.txt
	$(PYTHON) tests/test_game.py

mac65: all
	$(PYTHON) tools/mac65-listing.py

clean:
	rm -rf build
