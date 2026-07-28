.PHONY: install fetch validate test demo-corruption demo-restore clean

VENV_PY := .venv/Scripts/python.exe

install:
	python -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements.txt

fetch:
	$(VENV_PY) scripts/fetch_data.py

validate:
	$(VENV_PY) scripts/build_and_run_suite.py

test:
	$(VENV_PY) -m pytest tests/ -q

demo-corruption:
	$(VENV_PY) scripts/inject_corruption.py
	-$(VENV_PY) scripts/build_and_run_suite.py

demo-restore:
	$(VENV_PY) scripts/inject_corruption.py --restore
	$(VENV_PY) scripts/build_and_run_suite.py

clean:
	rm -rf gx/uncommitted/validations gx/uncommitted/data_docs
