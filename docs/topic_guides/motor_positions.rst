Motor Positions
===============

Haven is able to save the positions of one of more motors in a
database; the saved positions can then be recalled later. The
following functions are related to motor positions:

- :py:func:`~haven.motor_position.save_motor_position`
- :py:func:`~haven.motor_position.list_motor_positions`
- :py:func:`~haven.motor_position.recall_motor_position`

.. contents::

Saving a Motor Position
-----------------------

To save the position of one or more motors, call
:py:func:`~haven.motor_position.save_motor_position()` with the motors
to be saved as arguments. These arguments can either be the name of a
previously instantiated :py:class:`ophyd.Device` object, or the
:py:class:`~ophyd.Device` itself. A keyword-only *name* argument is
also necessary, which should be a short, human-readable description of
the motor position.

.. code:: python

   import haven
   # An example of using the motor names to save the position
   uid = haven.save_motor_position("Aerotech_vert", "Aerotech_horiz", name="CuO A")

.. code:: python

   import ophyd
   import haven
   # An example of using the ophyd Devices to save the position
   aerotech_vert = ophyd.EpicsMotor("25idd:m1")
   aerotech_horiz = ophyd.EpicsMotor("25idd:m2")
   uid = haven.save_motor_position(aerotech_vert, aerotech_horiz, name="CuO A")
   
:py:func:`~haven.motor_position.save_motor_position()` returns the
database ID of the document that was created. This **ID is the best
way to retrieve a motor position** from the database later, though it
can be also be retrieved using the *name* argument provided it is
unique.

Saving All Motor Positions
^^^^^^^^^^^^^^^^^^^^^^^^^^

It may be convenient to save all motor positions to the database as a
sort of checkpoint before performing some non-routine operation. This
can be done with the following line. Future work will provide a
shorted version. **Remember to call**
:py:func:`~haven.devices.load_instrument.load_instrument()`
**first**.

.. code:: python

    haven.save_motor_position(*haven.registry.findall(label="motors"), name="checkpoint before replacing monochromator")


Viewing Saved Motor Positions
-----------------------------

The function :py:func:`~haven.motor_position.list_motor_positions()`
will print out a list of all the saved motor positions. This list also
contains the database ID for each position, in case that information
was not retained when saving the motor position originally.


Recalling a Saved Motor Position
--------------------------------

The beamline can be set back a previously saved motor position using
the :py:func:`haven.motor_position.recall_motor_position()`
function. **This function is a bluesky-style plan**, and so the plan
**must be passed to a RunEngine** to be effective.

The saved motor position can be retrieved using either the
ID generated when the position was saved (the *uid* argument), or by
the *name* argument that was chosen when the position was saved. **If
the *name* is not unique**, no guarantee is made regarding which motor
position is restored.

.. code:: python
	  
    import haven
    RE = haven.RunEngine()

    # Save the motor position
    uid = haven.save_motor_position("Aerotech_vert", name="start position")

    # Restore the motor position
    plan = haven.recall_motor_position(uid=uid)
    RE(plan)


The MotorPosition Data Model
----------------------------

:py:class:`haven.motor_position.MotorPosition` is a pydantic model
that represents a set of motor positions in the database. Any
attribute that has a type definition (e.g. ``offset: float = None``)
is a data attribute and can be saved to the database.

To **add a new database value**, add the appropriate attribute to the
pydantic model, and modify the
:py:meth:`~haven.motor_position.MotorPosition.save()` and
:py:meth:`~haven.motor_position.MotorPosition.load()` methods to
accomodate the new database value.
