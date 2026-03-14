"""Domain model package."""

COORDINATE_SYSTEMS = ["Cartesian", "Cylindrical"]
BOUNDARY_TYPES = ["PML_8", "MUR", "PEC", "PMC"]
PORT_TYPES = ["Lumped", "Waveguide", "PlaneWave"]
DUMP_TYPES = ["EField", "HField", "NF2FF"]
EXCITATION_TYPES = ["Gaussian", "Sinusoid"]

DEFAULTS = {
	"simulation": {
		"coordinate_system": "Cartesian",
		"delta_unit": 1e-3,
		"nr_ts": 100000,
		"end_criteria": 1e-5,
		"excitation_type": "Gaussian",
		"excitation_f0": 1e9,
		"excitation_fc": 5e8,
		"solver_executable": "",
		"solver_arguments": "",
		"run_blocking": True,
	},
	"material": {
		"epsilon_r": 1.0,
		"mu_r": 1.0,
		"kappa": 0.0,
		"is_pec": False,
	},
	"boundary": {
		"xmin": "PML_8",
		"xmax": "PML_8",
		"ymin": "PML_8",
		"ymax": "PML_8",
		"zmin": "PML_8",
		"zmax": "PML_8",
		"pml_cells": 8,
	},
	"port": {
		"port_type": "Lumped",
		"port_number": 1,
		"resistance": 50.0,
		"excite": True,
		"propagation_direction": "+z",
		"start_x": 0.0,
		"start_y": 0.0,
		"start_z": 0.0,
		"stop_x": 0.0,
		"stop_y": 0.0,
		"stop_z": 1.0,
	},
	"grid": {
		"coordinate_system": "Cartesian",
		"base_resolution": 1.0,
		"max_resolution": 5.0,
		"grading_factor": 1.3,
		"auto_smooth": True,
	},
	"dumpbox": {
		"dump_type": "EField",
		"enabled": True,
		"frequency_spec": "1e9,10e9",
	},
}
