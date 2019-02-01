include $(SRC_DIR)/Makefile.inc

PYFLAKES = $(PYTHON_DIR)/bin/pyflakes
NOSE = $(PYTHON_DIR)/bin/nosetests

test:
	$(PYFLAKES) $(SRC_DIR)/python
	$(NOSE) $(SRC_DIR)/python/lib/db/

all:
	echo nothing...


