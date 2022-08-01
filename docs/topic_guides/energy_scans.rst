############################
Running Energy Scans (XAFS)
############################

:py:func:`~haven.plans.xafs_scan.xafs_scan()` for Straight-Forward XAFS Scans
=============================================================================

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

For extra flexibility, use the
:py:func:`~haven.plans.energy_scan.energy_scan()` plan, which accepts
a sequence of energies to scan. For example, to scan from 8325
to 8375 eV in 1 eV steps:

.. code-block:: python

   energies = range(8325, 8376, step=1)
   RE(energy_scan(energies))

Notice the range ends at 8376 eV instead of 8375 eV, since the last
value is not included when using a ``range``.

The *exposure* time can also be given. *exposure* can either be a
single number to be used for all energies, or a sequence of numbers
with the same length as *energies*, and each energy will use the
corresponding exposure:

.. code-block:: python

    import numpy as np
    energies = range(8325, 8376, step=1)
    exposures = np.linspace(0.5, 5, num=len(energies))
    RE(energy_scan(energies), exposure=exposures)
   
Building a more complicated set of energies can be made simpler using
the :py:class:`~haven.energy_ranges.ERange` helper class:

.. code-block:: python

    energies = ERange(8325, 8375, E_step=1).energies()
    RE(energy_scan(energies))

To make things even easier,
:py:func:`~haven.plans.energy_scan.energy_scan()` can accept energy
range objects directly:

.. code-block:: python

    energies = [
        8300, 8320,  # Individual energies are okay too, you can mix and match
        ERange(8325, 8375, E_step=0.5),
	ERange(8375, 8533, E_step=5),
    ]
    RE(energy_scan(energies))

Other than including the ending energy in the list, this usage does
not provide considerable value. However, the inclusion of multiple
energies with different exposure times makes the value more clear,
since *energy_scan* will automatically replace an
:py:class:`~haven.energy_ranges.ERange` instance with the result of
the instance's :py:meth:`~haven.energy_ranges.ERange.energies()`
method, and add equivalent entries into *exposure* based on the
instance's :py:meth:`~haven.energy_ranges.ERange.exposures()` method.

.. code-block:: python

    energies = [
        ERange(8325, 8375, E_step=0.5, exposure=1.5),
	ERange(8375, 8533, E_step=5, exposure=0.5),
    ]
    RE(energy_scan(energies))		

There is also a similar :py:class:`~haven.energy_ranges.KRange` that
works similarly except using electron wavenumbers (k) instead of X-ray
energy. This allows the energies to be given in a more intuitive way
for EXAFS:

.. code-block:: python

    energies = [
        ERange(-50, 50, E_step=0.5, exposure=1.5),
        ERange(50, 200, E_step=5, exposure=0.5),
        KRange(200, 14, k_step=0.05, , k_weight=1., exposure=1.),
    ]
    RE(energy_scan(energies, E0=8333))

Notice that the energies are now given relative to the edge energy
*E0* (the nickel K-edge in this case). This is almost always necessary
when using a :py:class:`~haven.energy_ranges.KRange` instance, since
otherwise the corresponding energies would be relative to a free,
zero-energy electron, instead of core electrons. *E0* can also be
given as a string, in this case ``E0="Ni_K"``.

At this point, we have largely replicated the behavior of
:py:func:`~haven.plans.xafs_scan.xafs_scan()` described above. In
fact, :py:func:`~haven.plans.xafs_scan.xafs_scan()` is a wrapper
around :py:func:`~haven.plans.energy_scan.energy_scan()` whose main
purpose is to take the parameters in the form of ``(energy, step,
exposure, energy, ...)``, and convert them to
:py:class:`~haven.energy_ranges.ERange` and
:py:class:`~haven.energy_ranges.KRange` instances.


Changing Detectors or Positioners
=================================
