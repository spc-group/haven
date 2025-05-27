=====================================
Tutorial: XAFS Scans and Energy Scans
=====================================

This notebook shows the following tasks:

- :ref:`single-segment-xanes`
- :ref:`multi-segment-xafs`
- :ref:`multi-segment-exafs`
- :ref:`modifying-detectors`

First we have to **setup haven**, the beamline control library. Haven
contains most of the tools we will use. We can import haven, setup the
instrument, and create the run engine with the ``start_haven``
command. After the required steps are completed, it will deliver us
into an ipython terminal.


.. _single-segment-xanes:
   
Running a Single-Segment XANES scan
===================================

Running a scan in bluesky is a **two step process**.

First, **create a plan**. A plan generates messages with instructions
to do things like move a motor, wait for a motor to arrive at its
destination, and trigger and read a detector. To create a plan, you
call a function that will generate these messages. **Calling the
function doesn't actually execute the scan.** In our case,
``plans.xafs_scan([], ("E", 8325, 0.5, 8350, 1.))`` will create the plan, but the
plan will not do anything unless used with a run engine.

The :py:func:`~haven.plans._xafs_scan.xafs_scan()` plan requires scan
regions with four values: *(start, stop, stop, step,
exposure)*. *start* and *stop* mark the boundaries of the energy
range, in eV. *step* is the space between energy points, in eV. Unless
the range between *start* and *stop* is a whole multiple of *step*,
the *stop* energy will not appear in the scan. *exposure* is the time,
in seconds, for which to count at each energy.

The optional argument *E0* specifies the energy, in eV, of an x-ray
absorbance edge. If given, all other energy values (i.e. *start* and
*stop*) will be relative to *E0*.

.. code-block:: python

   >>> # These two plans will scan from 8323 eV to 8383 eV
   >>> #   in 2eV steps with 1 sec exposure
   >>> absolute_plan = haven.xafs_scan([], ("E", 8323, 8383, 2, 1))
   >>> relative_plan = haven.xafs_scan([], ("E", -10, 50, 2, 1) E0=8333)

Before running either of these plans, we can **verify that it will do
what we expect** with the
:py:func:`~bluesky.simulators:summarize_plan()` helper. This function
will print a human-readable description of all the steps that will be
taken.

.. code-block:: python

   >>> summarize_plan(relative_plan)

Next, **execute the plan on the run engine**. As part of
``start_haven``, we created a run engine. Now we will use this run
engine to execute the plan. The run engine will read the messages and
perform the appropriate tasks. We will also provide some meta-data,
which will allow us to determine the purpose of these scans in the
future. :py:func:`~bluesky.simulators:summarize_plan()` consumed the
plan so we have to create a new one.

When the run engine finishes the plan, it will return a unique
identifier (UID). This UID is the best way to retrieve the data from
the database. We will **save the UID** to a variable, and also print
it to the page in case we want to recall it later.

We will also pass the ion chambers as the list of detectors in order
to collect some real data.

.. code-block:: python

   >>> plan = haven.xafs_scan(ion_chambers, ("E", -20, 50, 2, 1), E0=8333)
   >>> # Run one of the plans with the previously created RunEngine
   >>> uid = RE(plan, sample_name="Ni foil", purpose="training")
   >>> print(uid)
   

.. _multi-segment-xafs:
   
Running a Multi-Segment XAFS Scan
=================================

The ``xafs_scan()`` function can accept multiple sets of values to
accomodate additional scan regions. After the first set of four
parameters (*start*, *stop*, *step*, *exposure*), additional sets can
be given as tuples.

Additionally, Haven will look up the literature energy for a given
X-ray absorption edge, in this case the Ni K-edge.

The call below will scan the following energies, relative to 8333 eV:

- -50 to -10 eV (8283 to 8323 eV) in 5 eV steps with 0.5 sec exposure
- -10 to +50 eV (8323 to 8383 eV) in 1 eV steps with 1 sec exposure
- +50 to +200 eV (8383 to 8533 eV) in 10 eV steps with 0.5 sec exposure


.. code-block:: python

   >>> multisegment_plan = haven.xafs_scan(
           ("E", -50, -10,  5, 0.5), # start, stop, step, exposure
           ("E", -10,  50,  1, 1),   # start, stop, step, exposure
           ("E",  50, 200, 10, 0.5), # start, stop, step, exposure
           E0="Ni_K"
       )
   >>> # Run the plan with the previously created RunEngine
   >>> uid = RE(multisegment_plan, sample_name="Ni foil", purpose="training")
   >>> print(uid)


.. _multi-segment-exafs:
   
Running a Multi-Segment EXAFS Scan in K-space
=============================================

The `xafs_scan()` function can also accept regions as X-ray
wavenumbers instead of X-ray energy. Each K-space region accepts an
additional parameter *k_weight* that produces increasing exposure
times at higher wavenumbers.

.. code-block:: python

   >>> k_start = haven.energy_to_wavenumber(30)
   >>> exafs_plan = haven.xafs_scan(
           ("E", -200,   -20,   5,    1),  # start, stop, step, exposure
           ("E",  -20,    30,   0.3,  1),  # start, stop, step, exposure
           ("k", k_start, 13.5, 0.05, 1.0, 0.5) # start, stop, step, exposure, k-weight
           E0=8331.0
       )
   >>> # Run the plan with the previously created RunEngine
   >>> uid = RE(exafs_plan, sample_name="Ni foil", purpose="training")
   >>> print(uid)


.. _modifying-detectors:

Modifying the List of Detectors
===============================

Typically, :py:func:`~haven.xafs_scan()` measures all registered ion
chambers, most likely those set up during
:py:func:`haven.load_instrument()` called above. However, this list
can be be any list of readable devices. The following example records
only ion chambers named "It", "I0", or "Iref". Modify these names to
suit your use case.

.. code-block:: python

   >>> detectors_plan = haven.xafs_scan(
           [It, I0, Iref],
	   ("E", 8323, 8383, 2, 1)
       )
   >>> # Run the plan with the previously created RunEngine
   >>> uid = RE(detectors_plan)
   >>> print(uid)
