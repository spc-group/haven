#######################
Fly Scanning
#######################

Fly scanning is when detectors take measuments from a sample while in 
motion. Creating a range of measurements based on user specified points.
This method is faster than traditional step scanning.

Flyscanning with Bluesky follows a general three method process

 - Kickoff: starts off a fly scan
 - Complete: checks whether flight is occuring until it is finished
 - Collect: retrieves data from fly scan as proto-events

Although Bluesky works of these methods alone it only takes the 
input of a flyer. Most of the work that is done for fly scanning is done 
with Ophyd. Because of Blueskys way of fly scanning, the Ophyd flyer device
needs the ``kickoff()``, ``complete()``, and ``collect()`` methods. Any 
calculation or configuration for fly scanning needs to be inside the 
Ophyd device as well.

Setting Up a Scan
=================
The fly scan only needs four input parameters to provide enough information
 - Start position: First point of scan expected to be measured
 - End position: Last point of scan expected to be measured
 - Step size: How many egu(microns) should a measument reflect
 - Dwell time: How long should each step be measured for
 
All other needed parameters are either grabbed from EPICS or calculated

Calculated Parameters Before Scan
==================================
There are a few calculated parameters to account for acceleration as well
as positioning user-set points to match PSO pulses

For a sample stage the following components need to be calculated: a taxi 
start/end position, the encoder window start/end, the step size in encoder
count units, and the motor position for PSO start.

The Taxi start and end are the physical start and end positons of the 
sample stage. This is to allow the sample to accelerate to target
velocity needed during scan.

The encoder window start/end is set to create a range for pulses during the scan.
As well as the encoder step size which tells the PSO when to sen pulses.

The PSO start determines the location of measurments.

Position-Synchronized Output(PSO) Pulses
========================================
PSO pulses are used to trigger hardware to begin a new bin of measurements.
They are are configured within the Ophyd flyer device, PSO pulses in the 
form of a 10 microsecond(us) on pulse. These pulses are then set to only
happen every multiple integer of encoder step counts. The pulses are also
set to only ocur within the encoder window. Although the scaler is able 
use this raw pules to create a bin, the fluorescence detector cannot. 
Instead, a digital delay generator is used to transform the pulse to a
steady high pulse that tells the detector to measure followed by a low pulse 
that starts a new measuement.

Physical Fly scan process
=========================
 1. Moves to PSO start
 2. Arms PSO and starts encoder count
 3. Moves to taxi start
 4. Begins accelerating until reaching speed at PSO start and starts flying
 5. PSO triggers detectors to take measurments until reaching a step
 6. Continues flight taking measurments until reaching the end of the 
    last measument at PSO end 
 7. Finally comes to a stop at taxi end after deccelerating





