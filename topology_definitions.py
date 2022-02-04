import pandas as pd
from read_input import read_top, read_topology
import numpy as np

# Import the topology informations
def raw_top(parameters):
	raw_topology_atoms, topol_bonds = read_topology(parameters)
	# To import the [ atoms ] section of the topology
	#atom_topology_num, atom_topology_type, atom_topology_resid, atom_topology_resname, atom_topology_name, atom_topology_mass  = protein_top.list_atoms()
	# This is needed when we want to do some stuff only to the N terminal
	first_resid = 'N_'+str(raw_topology_atoms['residue_number'][0])
	# this is used in greta
	#raw_topology_atoms = pd.DataFrame(np.column_stack([atom_topology_num, atom_topology_type, atom_topology_resid, atom_topology_resname, atom_topology_name, atom_topology_mass]), columns=['nr', 'type','residue_number', 'residue', 'atom', 'mass'])

	# Changing the mass of the atoms section by adding the H
	raw_topology_atoms['mass'].astype(float)

	# Adding H to backbone N
	mask = raw_topology_atoms['atom_type'] == 'N'
	raw_topology_atoms['mass'][mask] = raw_topology_atoms['mass'][mask].astype(float).add(1)
	# Adding an extra H to the N terminal
	mask = ((raw_topology_atoms['residue_number'] == raw_topology_atoms['residue_number'].min()) & (raw_topology_atoms['atom_type'] == 'N'))
	raw_topology_atoms['mass'][mask] = raw_topology_atoms['mass'][mask].astype(float).add(2)
	# Adding H to OH groups
	mask = raw_topology_atoms['atom_type'] == 'OA'
	raw_topology_atoms['mass'][mask] = raw_topology_atoms['mass'][mask].astype(float).add(1)

	# Aromatics (PHE/TYR/HIS/TRP)

	# Aromatic carbons dictionary
	aromatic_carbons_dict = {
		'PHE': ['CD1', 'CD2', 'CE1', 'CE2', 'CZ'],
		'TYR': ['CD1', 'CD2', 'CE1', 'CE2'],
		'HIS': ['CE1', 'CD2'],
		'TRP': ['CD1', 'CE3', 'CZ2', 'CZ3', 'CH2']
	}

	for resname, atomnames in aromatic_carbons_dict.items():
		for atom in atomnames:
			mask = ((raw_topology_atoms['residue'] == resname) & (raw_topology_atoms['atom'] == atom))
			raw_topology_atoms['mass'][mask] = raw_topology_atoms['mass'][mask].astype(float).add(1)

	# Structure based atomtype definition
	raw_topology_atoms['sb_type'] = raw_topology_atoms['atom'] + '_' + raw_topology_atoms['residue_number'].astype(str)

	# ACID pH
	# Selection of the aminoacids and the charged atoms (used for B2m)
	# TODO add some options for precise pH setting
	acid_ASP = raw_topology_atoms[(raw_topology_atoms['residue'] == "ASP") & ((raw_topology_atoms['atom'] == "OD1") | (raw_topology_atoms['atom'] == "OD2") | (raw_topology_atoms['atom'] == "CG"))]
	acid_GLU = raw_topology_atoms[(raw_topology_atoms['residue'] == "GLU") & ((raw_topology_atoms['atom'] == "OE1") | (raw_topology_atoms['atom'] == "OE2") | (raw_topology_atoms['atom'] == "CD"))]
	acid_HIS = raw_topology_atoms[(raw_topology_atoms['residue'] == "HIS") & ((raw_topology_atoms['atom'] == "ND1") | (raw_topology_atoms['atom'] == "CE1") | (raw_topology_atoms['atom'] == "NE2") | (raw_topology_atoms['atom'] == "CD2") | (raw_topology_atoms['atom'] == "CG"))]
	frames = [acid_ASP, acid_GLU, acid_HIS]
	acid_atp = pd.concat(frames, ignore_index = True)
	#this is used
	acid_atp = acid_atp['sb_type'].tolist()

	# BONDS
	# This list will be used to build pairs and exclusions lists to attach in the topology
	topology_bonds = topol_bonds.bond_pairs

	return raw_topology_atoms, first_resid, acid_atp, topology_bonds, raw_topology_atoms['atom_number'].to_list()






# Harp 0
# check all the masses in combination with the above stuff
gromos_atp = pd.DataFrame(
    {'name': ['O', 'OA', 'N', 'C', 'CH1', 
            'CH2', 'CH3', 'CH2r', 'NT', 'S',
            'NR', 'OM', 'NE', 'NL', 'NZ'],
     'at.num': [8, 8, 7, 6, 6, 6, 6, 6, 7, 16, 7, 8, 7, 7, 7],
     'c12': [1e-06, 1.505529e-06, 2.319529e-06, 4.937284e-06, 9.70225e-05, # CH1
            3.3965584e-05, 2.6646244e-05, 2.8058209e-05, 5.0625e-06, 1.3075456e-05,
            3.389281e-06, 7.4149321e-07, 2.319529e-06, 2.319529e-06, 2.319529e-06]
     }
)
gromos_atp.to_dict()
gromos_atp.set_index('name', inplace=True)

gromos_atp_c6 = pd.DataFrame(
    {'name': ['O', 'CH1', 'CH2', 'CH3'],
     'c6': [0.0022619536, 0.00606841, 0.0074684164, 0.0096138025]
    }
)
gromos_atp_c6.to_dict()
gromos_atp_c6.set_index('name', inplace=True)

# TODO make it more general (without the residue number)
# native reweight for TTR and ABeta. This dictionary will rename the amber topology to gromos topology
#gro_to_amb_dict = {'OC1_11' : 'O1_11', 'OC2_11':'O2_11'}
gro_to_amb_dict = {'OT1_42' : 'O1_42', 'OT2_42':'O2_42'}
