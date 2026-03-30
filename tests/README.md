Haven Tests
===========

Haven tests are split into several categories.

`haven/`
: Tests of the bluesky plans, ophyd-async devices, and similar.

`firefly/`
: Tests of the graphical user interface.

`integration/`
: Slow tests that combine multiple components. Requires the
  `--runslow` flag to pytest.
