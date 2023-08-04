#######################
Fly Scanning
#######################

Fly scanning is when detectors take measuments from a sample while in 
motion. Creating a range of measurements based on user specified points.
This method is faster than traditional step scanning.

Flyscanning with Bluesky follows a general three method process

 - Kickoff: Initializes flyable Ophyd devices to set themselves up and 
            start scanning
 - Complete: Continously checks whether flight is occuring until it is finished
 - Collect: Retrieves data from fly scan as proto-events

Although Bluesky works of these methods alone it only takes the 
input of a flyer. Most of the work that is done for fly scanning is done 
with Ophyd. Blueskys way of fly scanning requires the Ophyd flyer device
to have the ``kickoff()``, ``complete()``, and ``collect()`` methods. Any 
calculation or configuration for fly scanning needs to be inside the 
Ophyd device as well.

Setting Up a Scan
=================
The fly scan only needs four input parameters to be provided to the moving flyer
 - start_position: First point of scan expected to be measured
 - end_position: Last point of scan expected to be measured
 - step_size: How many egu(microns) should a measument reflect
 - dwell_time: How long should each step be measured for
 
This is done by choosing a flyer, such as aerotech.horiz, and running 
''aerotech.horiz.start_position.set(0)''

All other needed parameters are either grabbed from EPICS or calculated

Calculated Components Before Scan
---------------------------------
The sample stage flyer calculates the following components: slew speed,
a taxi start and end position, a PSO start and end position, the window 
start and end in encoder counts, and the step size in encoder count.

Because step siz and dwell time are input parameters, that means points
must be captured while the stage moves at a constant velocity otherwise
the measurments will have distorted lengths.

The Taxi start and end are the physical start and end positons of the 
sample stage. This is to allow the stage to accelerate to target
velocity needed during scan.

The encoder window start/end is set to create a range for pulses during the scan.
As well as the encoder step size which tells the PSO when to send pulses.

The PSO start/end determines the start of the first measument and the end 
of the last.

An array of PSO positions is also created to provide the location of each 
measured point.

Physical Fly scan process
-------------------------
1. Moves to PSO start
2. Arms PSO and starts encoder count
3. Moves to taxi start
4. Begins accelerating until reaching speed at PSO start and starts flying
5. PSO triggers detectors to take measurments until reaching a step
6. Continues flight taking measurments until reaching the end of the 
   last measument at PSO end 
7. Finally comes to a stop at taxi end after deccelerating

Position-Synchronized Output(PSO) Pulses
========================================
PSO pulses are used to trigger hardware to begin a new bin of measurements.
The Ophyd flyer device sends comands to the ensemble controller to configure
its settings. PSO pulses are sent in the form of a 10us on pulse. These pulses are then set to only
happen every multiple integer of encoder step counts. The pulses are also
set to only ocur within the encoder window. Although the scaler is able 
use this raw pules to create a bin, the fluorescence detector cannot. 
Instead, a digital delay generator is used to transform the pulse to a
steady high pulse that tells the detector to measure followed by a low pulse 
that starts a new measuement.

Notes
=====
If a scan crashes the velocity will need to be changed back to its previous
value in the setup caQtDM, otherwise the velocity will likely be very slow.







