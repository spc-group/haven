==========================
 Saving Data to XDI Files
==========================

.. note::

   This page is intended for beamline staff. If you are a user at a
   beamline using Haven, this is most likely already set up for you.

.. todo::

   - Put in links to the XDI specification

XAFS Data Interchange (XDI) is a standard file format for storing data
from individual XAFS scans in a plain-text file. Currently, Haven
supports **automatic saving of energy scans** using either the
:py:func:`~haven.plans.energy_scan.energy_scan()` or
:py:func:`~haven.plans.xafs_scan.xafs_scan()` functions. The filename
used for saving will be generated from metadata. For more refined
control, see below for how to create
:py:class:`~haven.xdi_writer.XDIWriter` objects, or even creating a
customized subclass of :py:class:`~haven.xdi_writer.XDIWriter`.

The XDI file is opened at the start of the scan, and **data are
written in real time** during data acquisition, so aborted plans will
still have data saved. Halted plans will still have data saved, but
**the file may remain open** with write intent until the python
interpreter running Haven is closed. This was a deliberate design
choice to ensure the XDI writer keeps an exclusive lock on the file
during execution of the plan.

Using the XDIWriter
===================

.. todo::

   - Put in a link to how bluesky callbacks work

If you want to save the XDI file to specific place or pass in other
arguments, you can create your own instance of the
:py:class:`~haven.xdi_writer.XDIWriter` class. The first argument to
:py:class:`~haven.xdi_writer.XDIWriter()` should be either a file
name, a :py:class:`pathlib.Path` object, or an open file like those
return by python's built-in ``open()``. The following 3 invocations
are all valid:

.. code-block:: python

   from haven import XDIWriter
   from pathlib import Path
   
   # Provide a regular string...
   writer = XDIWriter("/path/to/my/xafs_data.xdi")
   
   # ...or provide a Path object...
   root = Path("/path/to/my/")
   writer = XDIWriter(root / "xafs_data.xdi")

The *filename* can contain placeholders that will be filled in once
the plan starts. This works similarly to python's format string
syntax. For example:

.. code-block:: python

   from haven import XDIWriter
   
   plan = energy_scan(..., E0="Ni_K", md=dict(sample_name="nickel oxide"))
   writer_callback = XDIWriter(fd="./{year}{month}{day}_{sample_name}_{edge}.xdi")
   RE(plan, writer)

Assuming the date is 2022-08-19, then the filename will become
"20220819_nickel-oxide_Ni_K.xdi".

.. todo::

   Describe how to find the valid placeholders from each plan.


Custom Subclasses of XDIWriter
==============================
