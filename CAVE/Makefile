
.PHONY: test
test:
	nosetests -sv --with-coverage --cover-package=cave

.PHONY: test-fast
test-fast:
	nosetests -a '!slow' -sv --with-coverage --cover-package=cave

.PHONY: test-runtimes
test-runtimes:
	# requires nose-timer
	nosetests -sv --with-timer --timer-top-n 15

.PHONY: doc
doc:
	make -C doc html

.PHONY: clean
clean: clean-data
	make -C doc clean
