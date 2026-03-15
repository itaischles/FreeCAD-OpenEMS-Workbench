# Description of openEMS workbench in FreeCAD

## Summary
The steps to carry out an openEMS analysis are:
	1. Preprocessing: setting up the analysis problem.
		1. Modeling the geometry: creating the geometry with FreeCAD. Importing a geometry from an external source may be implemented in the future.
		2. Creating an analysis.
			1. Setting the global simulation parameters. 
			2. Adding simulation boundary conditions.
			3. Adding materials to the parts of the geometric model.
			4. Adding ports for inputing energy into the simulation box.
			5. Defining excitation signals for the ports.
			6. Create probes (voltage\current).
			7. Creating a Yee grid (mesh) for the geometrical model.
	2. Solving: running an external solver from within FreeCAD.
	3. Postprocessing: visualizing the analysis results from within FreeCAD, or exporting the results so they can be postprocessed with another application.

Now we will explore in detail each step.

## Modeling the geometry
In this stage the user builds the structures that will be used in the simulation. This can be for example: generating a transmission line cable by creating a hollow cylinder with inner and outer radius for the shielding, an inner cylinder, concentric with the shielding to model the inner wire of the coaxial cable. Then, perhaps inserting a hollow cylinder in between them to model the dielectric, etc...

## Creating an analysis
The user then opens the openEMS workbench and creates an analysis object. The analysis object is a container of the entire FDTD simulation. Inside this container will be several objects that will be listed next.

## Simulation object
The simulation object contains information about the simulation:
	1. Number of simulation time steps.
	2. Time stepping information or frequency information (e.g., maximum time step, frequency range, etc.)
	3. Results folder

## Boundary conditions
The boundary conditions are calculated on a box that contains the entire set of simulated objects (geometry). This boundary box is calculated automatically and updated with respect to the objects included in the analysis. The user sets 6 boundary conditions for x-min, x-max, y-min, y-max, z-min, z-max. The user can choose between different boundary conditions as defined in the openEMS documentation.

## Adding and assigning materials
The user adds materials to the simulation. Currently, the dielectric materials should have the following properties:
	1. epsilon_r: relative permittivity [unitless]
	2. mu_r: relative magnetic permeability [unitless]
	3. rho: resistivity [Ohm*meter]
Alternatively, the user can choose a perfect electrical conductor material (PEC). In the future, other materials will be included (Drude material, Lorentz material, ...)
After adding these materials to the analysis, the user assigns them to the geometries he created earlier.

## Adding ports
The user can choose between 2 different port types:
1. Lumped-element port:
	This port is characterized by its start and end point and its impedance, Z, which gives the constraint between the voltage and the current calculated between these two points. This port is automatically assinged with a probe that senses its voltage and current.
2. Waveguide port:
	This port is characterized by either a circular or rectangular (in this version) cross section. The electric and magnetic fields are analytically calculated for the first mode in the desired geometry. The user can also select a circular/rectangular geometrical object and set the port parameters to coincide with the geometry (e.g. selecting the outermost diameter of the shielding of the coaxial cable and setting the waveguide port to that face). The waveguide port also has an automatically generated probe for the voltage (integral along the E field lines from the inner to the outer conductor) and the current (close loop line integral of the magnetic field H around the inner conductor). 

Each port gets a unique port number.

## Defining excitation signals
This is where the user sets the temporal behavior of the voltage and/or current that is assigned to a specific port defined earlier. The user can select between some default functional behaviors such as:
	1. Sinusoidal signal (amplitude, frequency, phase).
	2. Gaussian pulse (amplitude, center, width).
	3. Rectangular pulse (rise/fall time, delay, flat-top width, flat-top amplitude).
More options for input excitation behaviors will be implemented in the future as well as the option to provide explicit functional forms.

## Voltage/current probes
The user can provide a line over which the E field will be integrated to get the voltage and thereby setting a voltage probe. Also the user can provide a closed path for a current probe.

## Yee grid (mesh)
A cartesian grid is constructed inside the simulation bounding box. This grid defines the Yee cells for the FDTD algorithm.
For the grid setup read: https://wiki.openems.de/index.php/FDTD_Mesh.html.

## Running the simulation
The openEMS FDTD solver will be triggered to run from within the openEMS workbench in FreeCAD. A live view of the solver output during the simulation run is generated in the FreeCAD report view.

## Postprocessing
The results of the simulation are saved in a dedicated folder provided in the "simulation" object of the analysis by the user before the simulation started. The generated output can include (depending on user choice):
	1. Field dumps. Either 3D, 2D, or 1D.
	2. Probe signals vs. the simulation time.
	3. Log file of the simulation.