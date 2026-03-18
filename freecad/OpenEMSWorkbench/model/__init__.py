"""Domain model package."""

COORDINATE_SYSTEMS = ["Cartesian", "Cylindrical"]
BOUNDARY_TYPES = ["PML_8", "MUR", "PEC", "PMC"]
PORT_TYPES = ["Lumped", "Waveguide", "PlaneWave"]
SIMULATION_BOX_FACE_CHOICES = ["XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"]
DUMP_TYPES = ["EField", "HField", "NF2FF"]
EXCITATION_TYPES = ["Gaussian", "Sinusoid", "Custom"]

DEFAULTS = {
	"simulation": {
		"coordinate_system": "Cartesian",
		"delta_unit": 1e-3,
		"nr_ts": 100000,
		"end_criteria": 1e-5,
		"excitation_type": "Gaussian",
		"excitation_f_max": 3e9,
		"max_simulation_time": 100e-9,
		"excitation_f0": 1e9,
		"excitation_fc": 5e8,
		"sinusoid_amplitude": 1.0,
		"sinusoid_frequency": 1e9,
		"sinusoid_phase_deg": 0.0,
		"gaussian_amplitude": 1.0,
		"gaussian_sigma": 1e-9,
		"gaussian_delay": 4e-9,
		"custom_expression": "",
		"solver_executable": "",
		"solver_arguments": "",
		"run_blocking": True,
	},
	"material": {
		"epsilon_r": 1.0,
		"mu_r": 1.0,
		"kappa": 0.0,
		"is_pec": False,
		"assignment_priority": 0,
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
		"simulation_box_face": "ZMin",
		"source_plane_offset_cells": 3,
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
		"mesh_base_step": 1.0,
		"mesh_max_step": 5.0,
		"mesh_growth_rate": 1.3,
		"mesh_auto_smooth": True,
		"mesh_preview_line_cap": 96,
	},
	"dumpbox": {
		"dump_type": "EField",
		"enabled": True,
		"frequency_spec": "1e9,10e9",
	},
}
