############################
Running Energy Scans (XAFS)
############################

:py:func:`~haven.plans.xafs_scan.xafs_scan()` for Straight-Forward XAFS Scans
===============================================

The :py:func:`~haven.plans.xafs_scan.xafs_scan()` is a bluesky plan
meant for scanning energy over a a number of energy ranges, for
example the pre-edge, edge, and EXAFS signal of a K-edge.

The function accepts an arbitrary number of parameters for defining
the ranges. The parameters are expected to provide energy step sizes
(in eV) and exposure times (in sec) between the boundaries of the
ranges. They should be passed following the pattern:

``energy, step, exposure, energy, step, exposure, energy, ...``

An example across the Nickel K-edge at 8333 eV could be:

.. code:: python

    RE(xafs_scan(8313, 2, 1, 8325, 0.5, 2, 8365, 10, 1.5, 8533))

``RE`` is the bluesky :py:class:`~bluesky.run_engine.RunEngine`, which
should already be imported for you in the ipython environment.


Absolute vs. Relative Scans
---------------------------

In some cases, it is more intuitive to describe the energy ranges
relative to some absorption edge (*E0*). The energy of the edge can be
given directly to :py:func:`~haven.plans.xafs_scan.xafs_scan` as *E0*,
then all energy points will be interpreted as relative to this
energy. The same scan from above would be:

.. code:: python

    RE(xafs_scan(-20, 2, 1, -8, 0.5, 2, 32, 10, 1.5, 200, E0=8333))


Defining Scans in K-Space
=========================

For extended structure scans (EXAFS), it may be more helpful to define
the EXAFS region in terms of the excited electron's wavenumber
(k-space). This can be done with the keyword arguments *k_step*,
*k_exposure*, and *k_max*. Providing *E0* is necessary, since
otherwise wavenumbers will be calculated relative to 0 eV, and will
not produce sensible results.

.. code:: python

    RE(xafs_scan(-20, 2, 1, -8, 0.5, 2, 32, k_step=0.02, k_max=12, k_exposure=1., E0=8333))


Better quality results can sometimes be achieved by setting longer
exposure times at higher *k*. The *k_weight* parameter will scale the
exposure time geometrically with *k*. ``k_weight=0`` will produce
constant exposure times, and if ``k_weight=1`` then exposure will
scale linearly with *k*.

.. code:: python

    RE(xafs_scan(-20, 2, 1, -8, 0.5, 2, 32, k_step=0.02, k_max=12, k_exposure=1., k_weight=1, E0=8333))

:py:func:`~haven.plans.energy_scan.energy_scan()` for More Sophisticated Scans
==============================================================================

