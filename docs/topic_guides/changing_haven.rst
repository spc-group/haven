#########################################
Making Changes to Haven and Contributing
#########################################

Two Scenarios are likely when proposing changes to Haven:

* New feature or bugfix written in a development environment (preferred)
* Troubleshooting the beamline during beamtime

From a Development Environment
==============================

The preferred way to modify Haven is to fork the main repository on
github, make changes on a new branch, and then submit a pull request
back to the main repository. This section assumes you **have an active
github account** (if not, sign up for one first).

The following steps are **only required the first time** you work on
Haven. Once done, the forked repository and local environment can be
reused.

1. Install a git client on your local computer (e.g. `git`_ or  `Github Desktop`_)
2. Create a fork of the `main Haven repository`_
3. Clone the forked repository to your local computer (e.g. ``git clone git@github.com:canismarko/haven.git``)
4. Install an anaconda-like distribution environment (`mamba-forge`_ is recommended)
5. Create a new conda environment from *environment.yml* (e.g. ``mamba env create -n haven -f haven/environment.yml``)
6. Activate the newly created conda environment (e.g. ``mamba activate haven``)
7. Install haven in the environment (``pip install -e "haven[dev]"``)
8. Verify that the :ref:`test-suite passes<Running Tests>`

The following steps should then be performed every time a new feature
is being added or bug is being fixed.

9. Sync your github fork with the main github repository
10. Pull changes to your local repository (``git pull``)
11. Create a new git branch for the task you are doing (e.g. ``git checkout -b area_detector_support``)
12. Make changes to the Haven source code as needed
13. Ensure all tests pass (``pytest``)
14. Commit changes to your local branch (``git add file1.py file2.py ...`` and ``git commit``)
15. Push changes back to github (``git push``)
16. Create a pull request on github to send changes back to the main repository.

.. _mamba-forge: https://mamba.readthedocs.io/en/latest/installation.html
.. _main Haven repository: https://github.com/spc-group/haven
.. _git: https://git-scm.com/download/
.. _Github Desktop: https://desktop.github.com/

.. _running tests:

Running Tests
-------------

*Pytest* is the recommended runner for Haven. Once the environment is
properly setup, the tests can be run using:

.. code-block:: console

   $ pytest

``pytest`` should not report any errors or failures, though skipped,
xfailed, and warnings are expected.

While running the tests, devices created using
:py:func:`~haven.devices.device.make_device()` will be replaced
with simulated devices using Ophyd's *sim* module. This means that
:py:func:`~haven.devices.load_instrument()` can be called without
hardware being present, and the corresponding fake devices can be
found in the :py:obj:`haven.registry`.

Additionally, some pytest fixtures are provided that create simulated
devices, (e.g. ion chambers) and can be used directly in your tests.

More details can be found in the file *haven/tests/conftest.py*.
       
From the Beamline
=================

.. warning::

   This section is intended for qualified beamline staff. **Users are
   not authorized** to make changes to the beamline software without
   staff involvement.

   If at all possible, changes should be made through a development
   environment as described above.

User support often requires changes to be made quickly from the
beamline computers.

*Git* is our version control software. It interacts with github, and
allows changes to the source code to be tracked and managed.

**Before modifying Haven**, create a new branch using git. This will
allow changes to be undone or pushed to github for use at other
beamlines. First we will create the new branch, then we will check it
out to begin working on it.

.. code-block:: console

    $ cd ~/haven
    $ git branch broken_shutter_workaround
    $ git checkout broken_shutter_workaround

Now modify the Haven scripts as needed to get the beamline
running. Once the changes are complete, **commit them to version
control**. If **new files have been added**, then we have to inform
git that they should be included, for examples:

.. code-block:: console

   $ git add haven/shutter_workaround.py

Then **commit the changes**:

.. code-block:: console

    $ git commit -a -m "Workaround for the shutter not also closing when requested."

If you see ``black...Failed``, then you need to run the command
again. Black is an add-on that enforces its own code format so that we
can focus on the important stuff, and it runs every time changes are
committed. If code needs to be reformatted, it stops the commit and
fixes the formatting. Attempting the commit again with the reformatted
code usually works.

The ``-a`` option tells git to automatically include all files that
have been changed. The ``-m`` option lets us include a short message
describing the commit. Please **write descriptive commit
messages**. For longer messages, omit the -m option (just ``git commit
-a``) and a text editor will appear.

Now the new branch can be pushed to github with

.. code-block:: console

    $ git push -u origin delete_me

The ``-u`` option is only needed the first time: it tells git to
connect the new branch to github (origin).


Design Defense
==============

An important consideration is how to manage changes to the code-base
in a way that satisfies several goals:

1. maximize reuse of code between beamlines (9-BM, 20-BM, and 25-ID)
2. support rapid troubleshooting at the beamline
3. control deployment of new features among the beamlines
4. encourage documentation and testing

Rapid troubleshooting necessarily leads to the code-base being in an
untested state, and so these changes should not automatically apply to
the code-base in use at another beamline.

The idea presented here is to have each beamline own a local copy of
the haven repository. Changes made at the beamline should ideally be
made to a separate branch. If the change is worth keeping it can be
committed along with documentation and tests, and the new branch can
be merged into the main branch.

Getting those changes to the other beamlines can be done whenever no
experiments are taking place there. We can pull the changes from
github, and run the system tests.

Using a common network folder for the scripts would satisfy
requirements 1 and 2, but not 3 and 4. Having entirely separate sets
of scripts would satisfy requirement 2, but not 1, 3, or 4. The
approach described here aims to strike a balance between the 4
requirements.
