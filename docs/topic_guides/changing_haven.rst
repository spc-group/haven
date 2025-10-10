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
4. `_Install Pixi`_ for environment management
5. Verify that the :ref:`test-suite passes<Running Tests>`

The following steps should then be performed each time a new feature
is being added or bug is being fixed.

6. Sync your github fork with the main github repository
7. Pull changes to your local repository (``git pull``)
8. Create a new git branch for the task you are doing (e.g. ``git checkout -b area_detector_support``)
9. Write tests for the new feature or fix.
10. Verify that the tests fail (``pixi run test-haven`` or ``pixi run test-firefly``)
11. Implement the feature/fix until tests pass.
12. Ensure all tests and linters pass (``pixi run test-all``)
13. Commit changes to your local branch (``git add file1.py file2.py ...`` and ``git commit``)
14. Push changes back to github (``git push``)
15. Create a pull request on github to send changes back to the main repository.

.. _mamba-forge: https://mamba.readthedocs.io/en/latest/installation.html
.. _main Haven repository: https://github.com/spc-group/haven
.. _Install Pixi: curl -fsSL https://pixi.sh/install.sh | sh
.. _git: https://git-scm.com/download/
.. _Github Desktop: https://desktop.github.com/

.. _running tests:

Running Tests
-------------

*Pytest* is the recommended runner for Haven. Pixi has tasks defined
for running tests:

.. code-block:: console

    $ pixi run test-haven
    $ pixi run test-firefly

``pytest`` should not report any errors or failures, though skipped,
xfailed, and warnings are expected.

To **run all tests** and also check **formatting**, **imports**, **type-hints**, and more, use

.. code-block:: console

    $ pixi run test-all

While running the tests, devices created using
:py:func:`~haven.devices.device.make_device()` will be replaced with
mocked devices using ophyd-async's. This means that
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

User support sometimes requires changes to be made quickly from the
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

   $ git add src/haven/shutter_workaround.py

Then **commit the changes**:

.. code-block:: console

    $ git commit -a -m "Workaround for the shutter not also closing when requested."

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
