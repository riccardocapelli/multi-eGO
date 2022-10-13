import MDAnalysis as mda
from MDAnalysis.analysis import distances
import numpy as np
import pandas as pd
import itertools
import parmed as pmd
from read_input import random_coil_mdmat, plainMD_mdmat
from topology_parser import read_topology, topology_parser, extra_topology_ligands
import plotly.express as px
from tqdm import tqdm

pd.options.mode.chained_assignment = None  # default='warn'
pd.options.mode.chained_assignment = 'warn' 


gromos_atp = pd.DataFrame(
    {'name': ['O', 'OA', 'N', 'C', 'CH1', 
            'CH2', 'CH3', 'CH2r', 'NT', 'S',
            'NR', 'OM', 'NE', 'NL', 'NZ'],
     'at.num': [8, 8, 7, 6, 6, 6, 6, 6, 7, 16, 7, 8, 7, 7, 7],
     #'c12': [1e-06/3.8, 1.505529e-06/3, 2.319529e-06/2.65, 4.937284e-06/1.9, 9.70225e-05/1.48), # CH1
     #       3.3965584e-05/2.2, 2.6646244e-05/3.1, 2.8058209e-05/2.35, 5.0625e-06/1.95, 1.3075456e-05/4.8,
     #       3.389281e-06/2.25, 7.4149321e-07/4.3, 2.319529e-06/2.65, 2.319529e-06/2.65, 2.319529e-06/2.65],
     'c12': [0.263158e-06, 0.501843e-06, 0.875294e-06, 2.598570e-06, 6.555574e-05, # CH1
             1.543890e-05, 8.595562e-06, 1.193966e-05, 2.596154e-06, 0.272405e-05, 
             1.506347e-06, 1.724403e-07, 0.875294e-06, 0.875294e-06, 0.875294e-06]
     #'c12': [1e-06/3.8, 1.505529e-06/3, 2.319529e-06/2.5, 4.937284e-06/1.9, 9.70225e-05(C/2), # CH1
     #       3.3965584e-05(C/2), 2.6646244e-05(C/2), 2.8058209e-05(C/2), 5.0625e-06/1.9, 1.3075456e-05/4.8,
     #       3.389281e-06/2.2, 7.4149321e-07/4.3, 2.319529e-06/2.5, 2.319529e-06/2.5, 2.319529e-06/2.5],
     #'c12': [0.263158e-06, 0.501843e-06, 0.892126e-06, 2.598570e-06, 2.598570e-06, # CH1
     #        2.598570e-06, 2.598570e-06, 2.598570e-06, 0.892126e-06, 0.272405e-05, 
     #        0.892126e-06, 1.724403e-07, 0.892126e-06, 0.892126e-06, 0.892126e-06]
     }
)
gromos_atp.to_dict()
gromos_atp.set_index('name', inplace=True)

class multiego_ensemble:
    #TODO insert the ego_native part since it is redundant
    '''
    This ensemble type gathers different topologies to make a single one.
    '''
    # Checklist of topology sections we need
    multiego_ensemble_top = pd.DataFrame()

    moleculetype = ''
    bonds = pd.DataFrame()
    bond_pairs = pd.DataFrame()
    angles = pd.DataFrame()
    dihedrals = pd.DataFrame()
    impropers = pd.DataFrame()
        
    ligand_bonds = pd.DataFrame()
    ligand_bond_pairs = []
    ligand_angles = pd.DataFrame()
    ligand_dihedrals = pd.DataFrame()

    pairs = pd.DataFrame()
    exclusions = pd.DataFrame()

    structure_based_contacts_dict = {
    }
    #    'random_coil' : pd.DataFrame(),
    #    'atomic_mat_plainMD' : pd.DataFrame(),
    #    'native_pairs' : pd.DataFrame(),
    #    'fibril_pairs' : pd.DataFrame(),
    #    'ligand_MD_pairs' : pd.DataFrame()
    #}

    greta_LJ = pd.DataFrame(columns=['; ai', 'aj', 'type', 'c6', 'c12', 'sigma', 'epsilon'])
    
    def __init__(self, parameters):
        self.parameters = parameters


    def multiego_wrapper():
        '''
        Check based on the attribute. Provides all the ensemble, check the attributes of each and then makes the merge 
        '''
        pass

    def add_ensemble_top(self, ensemble_toadd):
        '''
        This method allow the addition of atoms into the multi-eGO ensemble
        '''
        # ATOMTYPES
        ensemble_top = ensemble_toadd.ensemble_top.copy()
        ensemble_top['idx_sbtype'] = ensemble_top['sb_type']
        ensemble_top.set_index(['idx_sbtype'], inplace = True)
        ensemble_top.drop(columns=['index'], inplace=True)

        multiego_idx = self.multiego_ensemble_top.index
        ensemble_idx = ensemble_top.index
        diff_index = ensemble_idx.difference(multiego_idx)
        if not diff_index.empty:
            #print(f'\t- The following atoms are being inserted in multiego topology: {list(diff_index)}')
            print(f'\t- Inserting atoms in multiego ensemble')
        ensemble_top = ensemble_top.loc[diff_index]
        ensemble_top.sort_values(by=['atom_number'], inplace=True)
        self.multiego_ensemble_top = pd.concat([self.multiego_ensemble_top, ensemble_top], axis=0, sort=False)
    
        # Those will be recreated after the addition of all atoms, including the ligand ones
        type_c12_dict = self.multiego_ensemble_top[['sb_type', 'c12']].copy()
        type_c12_dict.rename(columns={'sb_type':'; type'}, inplace=True)
        type_c12_dict = type_c12_dict.set_index('; type')['c12'].to_dict()
        self.type_c12_dict = type_c12_dict

        return self
    
    
    def add_parsed_topology(self, ensemble_toadd):
        self.moleculetype = ensemble_toadd.parsed_topology.moleculetype.copy()
        self.bonds = ensemble_toadd.bonds.copy()
        self.bond_pairs = ensemble_toadd.bond_pairs.copy()
        self.angles = ensemble_toadd.angles.copy()
        self.dihedrals = ensemble_toadd.dihedrals.copy()
        self.impropers = ensemble_toadd.impropers.copy()
        self.system = ensemble_toadd.parsed_topology.system.copy()
        self.molecules = ensemble_toadd.parsed_topology.molecules.copy()
        
        return self

        
    def add_structure_based_contacts(self, name, contacts):
        '''
        Names to use: random_coil, atomic_mat_plainMD, native_pairs, fibril_pairs, ligand_MD_pairs
        '''
        self.structure_based_contacts_dict[name] = contacts
        # TODO questa funzione sotto si potrebbe anche togliere, mi sa che e' ridondante a quella sopra
        self.structure_based_contacts_dict = self.structure_based_contacts_dict
        return self

        
    def generate_multiego_LJ(self): # TODO nel self bisogna mettere i nomi degli MD ensembles
        
        # TODO ACID DEMMERDA
        #if parameters['acid_ff'] == True and top.acid_atp !=0:
        #        greta_LJ = greta_LJ[~greta_LJ.ai.isin(top.acid_atp)]
        #        greta_LJ = greta_LJ[~greta_LJ.aj.isin(top.acid_atp)]

        greta_LJ = pd.DataFrame()
        greta_MD_LJ = pd.DataFrame()
        greta_native_SB_LJ = pd.DataFrame()
        greta_fibril_SB_LJ = pd.DataFrame()
        ligand_MD_LJ = pd.DataFrame()
        
        # Get the md ensembles names
        for param, value in self.parameters.items():
            if 'md_ensemble' in param:
                greta_MD_LJ = MD_LJ_pairs(self.structure_based_contacts_dict[value], self.structure_based_contacts_dict['random_coil'], self.parameters, self.parameters[param])
                greta_LJ = pd.concat([greta_LJ, greta_MD_LJ], axis=0, sort=False, ignore_index=True)
    #    if not self.structure_based_contacts_dict['random_coil'].empty:
    #        if not self.structure_based_contacts_dict['atomic_mat_plainMD'].empty:
    #            greta_MD_LJ = MD_LJ_pairs(self.structure_based_contacts_dict['atomic_mat_plainMD'], self.structure_based_contacts_dict['random_coil'], self.parameters)
    #        if not self.structure_based_contacts_dict['native_pairs'].empty:
    #            # TODO to compute here the sb types and not in the fibril ensemble
    #            greta_native_SB_LJ = self.structure_based_contacts_dict['native_pairs']
    #        
    #        if not self.structure_based_contacts_dict['fibril_pairs'].empty:
    #            # TODO to compute here the sb types and not in the fibril ensemble
    #            greta_fibril_SB_LJ = self.structure_based_contacts_dict['fibril_pairs']
    #        
    #        if not self.structure_based_contacts_dict['ligand_MD_pairs'].empty:
    #            ligand_MD_LJ = self.structure_based_contacts_dict['ligand_MD_pairs']
    #    greta_LJ = pd.concat([greta_MD_LJ, greta_native_SB_LJ, greta_fibril_SB_LJ, ligand_MD_LJ], axis=0, sort=False, ignore_index=True)

        if greta_LJ.empty:
            greta_ffnb = greta_LJ 
            greta_lj14 = greta_LJ
        else:
            greta_ffnb, greta_lj14 = merge_and_clean_LJ(greta_LJ, self.type_c12_dict, self.parameters)
       
        self.greta_ffnb = greta_ffnb
        self.greta_lj14 = greta_lj14

        return self
        
    def generate_pairs_exclusions(self):
        # Here different bonds_pairs should be added:
        # from native and MD they should be the same, the ligand will be added.
        # Then here the pairs and exclusions will be made.

        bond_pairs = self.bond_pairs# + self.ligand_bond_pairs
        topology_pairs, topology_exclusions = make_pairs_exclusion_topology(self.multiego_ensemble_top, bond_pairs, self.type_c12_dict, self.parameters, 
                                                                            self.greta_lj14) 
        self.pairs = topology_pairs
        self.exclusions = topology_exclusions

        return self

    def add_parsed_ligand_topology(self, ensemble_toadd):
        '''
        This one will be kept separated by the protein parsed topology since the definitions are different
        '''
        self.ligand_moleculetype = ensemble_toadd.ligand_moleculetype.copy()
        self.ligand_topology = ensemble_toadd.ensemble_top.copy()
        self.ligand_bonds = ensemble_toadd.ligand_bonds.copy()
        self.ligand_bond_pairs = ensemble_toadd.ligand_pair_bonds.copy()
        self.ligand_angles = ensemble_toadd.ligand_angles.copy()
        self.ligand_dihedrals = ensemble_toadd.ligand_dihedrals.copy()
        
        # This is used when when want to read ligand pairs from the original topology
        # We might want to remove this part
        self.ligand_pairs = ensemble_toadd.ligand_pairs

        return self

    def list_acid_pH(self):
        # ACID pH
        # Selection of the aminoacids and the charged atoms (used for B2m)
        # TODO add some options for precise pH setting
        acid_ASP = self.ensemble_top[(self.ensemble_top['residue'] == "ASP") & ((self.ensemble_top['atom'] == "OD1") | (self.ensemble_top['atom'] == "OD2") | (self.ensemble_top['atom'] == "CG"))]
        acid_GLU = self.ensemble_top[(self.ensemble_top['residue'] == "GLU") & ((self.ensemble_top['atom'] == "OE1") | (self.ensemble_top['atom'] == "OE2") | (self.ensemble_top['atom'] == "CD"))]
        acid_HIS = self.ensemble_top[(self.ensemble_top['residue'] == "HIS") & ((self.ensemble_top['atom'] == "ND1") | (self.ensemble_top['atom'] == "CE1") | (self.ensemble_top['atom'] == "NE2") | (self.ensemble_top['atom'] == "CD2") | (self.ensemble_top['atom'] == "CG"))]
        frames = [acid_ASP, acid_GLU, acid_HIS]
        acid_atp = pd.concat(frames, ignore_index = True)
        #this is used
        self.acid_atp = acid_atp['sb_type'].tolist()
        return self


    def generate_outputs_toWrite(self):
        # Single and merge are right
        # Topol.top is left
        #pd.set_option('display.colheader_justify', 'left')
        pd.set_option('display.colheader_justify', 'right')

        self.moleculetype_toWrite = self.moleculetype.to_string(index=False)

        ffnonbonded_atp = self.multiego_ensemble_top[['sb_type', 'atomic_number', 'mass', 'charge', 'ptype', 'c6', 'c12']].copy()
        ffnb_colnames = ['; type', 'at.num', 'mass', 'charge', 'ptype', 'c6', 'c12']
        ffnonbonded_atp.columns = ffnb_colnames
        ffnonbonded_atp['c12'] = ffnonbonded_atp['c12'].map(lambda x:'{:.6e}'.format(x))
        self.ffnonbonded_atp_toWrite = ffnonbonded_atp.to_string(index = False)
        
        atomtypes_top = self.multiego_ensemble_top[['atom_number', 'sb_type', 'residue_number', 'residue', 'atom', 'cgnr']].copy()
        atomtypes_top.rename(columns = {'atom_number':'; nr', 'sb_type':'type', 'residue_number':'resnr'}, inplace=True)
        self.atomtypes_top_toWrite = atomtypes_top.to_string(index=False)
        
        atomtypes_atp = self.multiego_ensemble_top[['sb_type', 'mass']].copy()
        atomtypes_atp.rename(columns={'sb_type':'; type'}, inplace=True)
        self.atomtypes_atp_toWrite = atomtypes_atp.to_string(index = False, header = False)

        bonds = self.bonds
        bonds.rename(columns = {'ai':'; ai'}, inplace=True)
        self.bonds_toWrite = bonds.to_string(index=False)
        angles = self.angles
        angles.rename(columns = {'ai':'; ai'}, inplace=True)
        self.angles_toWrite = angles.to_string(index=False)
        dihedrals = self.dihedrals
        dihedrals.rename(columns = {'ai':'; ai'}, inplace=True)
        self.dihedrals_toWrite = dihedrals.to_string(index=False)
        impropers = self.impropers
        impropers.rename(columns = {'ai':'; ai'}, inplace=True)
        self.impropers_toWrite = impropers.to_string(index=False)
        pairs = self.pairs
        pairs.rename(columns = {'ai':'; ai'}, inplace=True)
        if(not pairs.empty):
            self.pairs_toWrite = pairs.to_string(index=False)
        else:
            self.pairs_toWrite = "" 
        exclusions = self.exclusions
        exclusions.rename(columns = {'ai':'; ai'}, inplace=True)
        if(not exclusions.empty):
            self.exclusions_toWrite = exclusions.to_string(index=False)
        else:
            self.exclusions_toWrite = "" 
        #self.system_toWrite = self.system.to_string(index=False)
        self.system_toWrite = self.parameters['protein']
        self.molecules_toWrite = self.molecules.to_string(index=False)

        if not self.parameters['egos'] == 'rc':
            atomtypes_top['; nr'] = atomtypes_top['; nr'].astype(str)
            atomtypes_top['resnr'] = atomtypes_top['resnr'].astype(int)
            # Dictionaries definitions to map values
            atnum_type_dict = atomtypes_top.set_index('type')['; nr'].to_dict()
            type_atnum_dict = atomtypes_top.set_index('; nr')['type'].to_dict()

            if self.parameters['ligand'] == True:
            
                ligand_atnum_type_df = self.ligand_topology[['sb_type']].copy()
                ligand_atnum_type_df['new_index'] = self.ligand_topology.index+1
                ligand_atnum_type_dict = ligand_atnum_type_df.set_index('sb_type')['new_index'].to_dict()
                atnum_type_dict = {**atnum_type_dict, **ligand_atnum_type_dict}

            self.greta_ffnb['ai_n'] = self.greta_ffnb['ai'].map(atnum_type_dict)
            self.greta_ffnb['aj_n'] = self.greta_ffnb['aj'].map(atnum_type_dict)
            self.greta_ffnb['ai_n'] = self.greta_ffnb['ai_n'].astype(int)
            self.greta_ffnb['aj_n'] = self.greta_ffnb['aj_n'].astype(int)
            # Here we want to sort so that ai is smaller than aj
            inv_greta_ffnb = self.greta_ffnb[['aj', 'ai', 'type', 'c6', 'c12', 'sigma', 'epsilon', 'same_chain', 'rc_probability', 'source', 'aj_n', 'ai_n']].copy()
            inv_greta_ffnb.columns = ['ai', 'aj', 'type', 'c6', 'c12', 'sigma', 'epsilon', 'same_chain', 'rc_probability', 'source', 'ai_n', 'aj_n']
            self.greta_ffnb = pd.concat([self.greta_ffnb,inv_greta_ffnb], axis=0, sort = False, ignore_index = True)
            self.greta_ffnb = self.greta_ffnb[self.greta_ffnb['ai_n']<=self.greta_ffnb['aj_n']]
            self.greta_ffnb.sort_values(by = ['ai_n', 'aj_n'], inplace = True)
            self.greta_ffnb = self.greta_ffnb.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')

            self.greta_ffnb.insert(5, '', ';')
            self.greta_ffnb = self.greta_ffnb.rename(columns = {'ai':'; ai'})
            self.greta_ffnb['epsilon'] = self.greta_ffnb["epsilon"].map(lambda x:'{:.6f}'.format(x))
            self.greta_ffnb['sigma'] = self.greta_ffnb["sigma"].map(lambda x:'{:.6e}'.format(x))
            self.greta_ffnb['c6'] = self.greta_ffnb["c6"].map(lambda x:'{:.6e}'.format(x))
            self.greta_ffnb['c12'] = self.greta_ffnb["c12"].map(lambda x:'{:.6e}'.format(x))
            self.greta_ffnb = self.greta_ffnb[['; ai', 'aj', 'type', 'c6', 'c12', '', 'sigma', 'epsilon', 'same_chain', 'rc_probability', 'source', 'ai_n', 'aj_n']]#, 'probability_std', 'distance_std']]
            self.greta_ffnb_toWrite = self.greta_ffnb.to_string(index = False)

        if self.parameters['ligand'] == True:
            self.ligand_moleculetype_toWrite = self.ligand_moleculetype.to_string(index=False)
            
            ligand_ffnonbonded_atp = self.ligand_topology[['sb_type', 'atomic_number', 'mass', 'charge', 'ptype', 'c6', 'c12']].copy()
            ffnb_colnames = ['; type', 'at.num', 'mass', 'charge', 'ptype', 'c6', 'c12']
            ligand_ffnonbonded_atp.columns = ffnb_colnames
            ligand_ffnonbonded_atp['c12'] = ligand_ffnonbonded_atp['c12'].map(lambda x:'{:.6e}'.format(x))
            ffnonbonded_atp = pd.concat([ffnonbonded_atp, ligand_ffnonbonded_atp], axis=0, sort=False, ignore_index=True)
            self.ffnonbonded_atp_toWrite = ffnonbonded_atp.to_string(index = False)

            ligand_atomtypes_top = self.ligand_topology[['atom_number', 'sb_type', 'residue_number', 'residue', 'atom', 'cgnr']].copy()
            #ligand_atomtypes_top['atom_number'] = list(range(1, len(ligand_atomtypes_top['atom_number'])+1))
            ligand_atomtypes_top['residue'] = 1
            ligand_atomtypes_top['cgnr'] = 1
            ligand_atomtypes_top.rename(columns = {'atom_number':'; nr', 'sb_type':'type', 'residue_number':'resnr'}, inplace=True)
            self.ligand_atomtypes_top_toWrite = ligand_atomtypes_top.to_string(index=False)
            ligand_bonds = self.ligand_bonds
            ligand_bonds.rename(columns = {'ai':'; ai'}, inplace=True)
            self.ligand_bonds_toWrite = ligand_bonds.to_string(index=False)
            ligand_angles = self.ligand_angles
            ligand_angles.rename(columns = {'ai':'; ai'}, inplace=True)
            self.ligand_angles_toWrite = ligand_angles.to_string(index=False)
            ligand_dihedrals = self.ligand_dihedrals
            ligand_dihedrals.rename(columns = {'ai':'; ai'}, inplace=True)
            self.ligand_dihedrals_toWrite = ligand_dihedrals.to_string(index=False)
            ligand_pairs = self.ligand_pairs
            ligand_pairs.rename(columns = {'ai':'; ai'}, inplace=True)
            ligand_pairs['c6'] = ligand_pairs['c6'].map(lambda x:'{:.6e}'.format(x))
            ligand_pairs['c12'] = ligand_pairs['c12'].map(lambda x:'{:.6e}'.format(x))
            self.ligand_pairs_toWrite = ligand_pairs.to_string(index=False)
            ligand_exclusions = self.ligand_pairs[['; ai', 'aj']].copy()
            self.ligand_exclusions_toWrite = ligand_exclusions.to_string(index=False)

        return self


class ensemble:
    '''
    Ensemble class: aggregates all the parameters used in the script.
    '''
    def __init__(self, parameters, ensemble_parameters, name):        
        # Topology Section
        # Atoms
        print('\t- Generating ensemble Atomtypes')
        print('\t- Reading topology and structure')
        self.name = name
        self.parameters = parameters
        self.ensemble_parameters = ensemble_parameters
        self.topology = pmd.load_file(ensemble_parameters[f'{name}_topology'], parametrize=False)
        self.structure = pmd.load_file(ensemble_parameters[f'{name}_structure'])


    def prepare_ensemble(self, add_native_ensemble = False):
        ensemble_top = prepare_ensemble_topology(self.topology, self.structure, self.ensemble_parameters, self.parameters)
        self.ensemble_top = ensemble_top
        print('\t- Ensemble topology generated')

        self.atoms_size = len(ensemble_top)

        sbtype_idx_dict = ensemble_top[['atom_number', 'sb_type']].copy()
        sbtype_idx_dict = sbtype_idx_dict.set_index('sb_type')['atom_number'].to_dict()
        self.sbtype_idx_dict = sbtype_idx_dict

        native_atomtypes = (ensemble_top['sb_type'] +':'+ ensemble_top['chain']).tolist()
        self.native_atomtypes = native_atomtypes
        
        type_c12_dict = ensemble_top[['sb_type', 'c12']].copy()
        type_c12_dict.rename(columns={'sb_type':'; type'}, inplace=True)
        type_c12_dict = type_c12_dict.set_index('; type')['c12'].to_dict()
        self.type_c12_dict = type_c12_dict

        idx_sbtype_dict = ensemble_top[['atom_number', 'sb_type']].copy()
        idx_sbtype_dict = idx_sbtype_dict.set_index('atom_number')['sb_type'].to_dict()
        self.idx_sbtype_dict = idx_sbtype_dict
    

    def assign_chains(self, atoms_size):
        print(f'\t- Reference structure size is {atoms_size} atoms')
        print(f'\t- This MD ensemble contains {self.atoms_size} atoms')
        if self.atoms_size%(atoms_size) == 0:
            number_of_chains = int(self.atoms_size/(atoms_size))
        else:
            print('Atoms does not allow chain assignment')
            exit()

        self.number_of_chains = number_of_chains

        print(f'\t- Number of chains {number_of_chains}')
        chain_column_list = []
        for chain in list(range(1, (number_of_chains+1))):
            for atom in range(atoms_size):
                chain_column_list.append(chain)

        ensemble_top = self.ensemble_top
        ensemble_top['chain'] = chain_column_list
        self.ensemble_top = ensemble_top
        
        idx_chain_dict = ensemble_top[['atom_number', 'chain']].copy()
        idx_chain_dict = idx_chain_dict.set_index('atom_number')['chain'].to_dict()
        self.idx_chain_dict = idx_chain_dict
        

    def get_parsed_topology(self):
        '''
        Topol.top sort of things except atoms. Namely bonds, angles, dihedrals, impropers, pairs and exclusions.
        This method uses the parser i wrote and not ParmEd.
        '''
        parsed_topology = topology_parser(read_topology(self.ensemble_parameters[f'{self.name}_topology']))

        # This one is self so i wrote less things in multiego and here
        self.parsed_topology = parsed_topology
        
        self.bonds = parsed_topology.bonds
        bond_pairs = parsed_topology.bond_pairs
        self.bond_pairs = bond_pairs
        self.angles = parsed_topology.angles
        self.dihedrals = parsed_topology.dihedrals
        self.impropers = parsed_topology.impropers


    def match_native_topology(self, sbtype_idx_dict):
        '''
        Fibril might not be entirely modelled, therefore the numbering does not match the native structure.
        Here a dictionary is supplied to renumber the atoms.
        '''

        print('\t- Renumbering the fibril atom numbers')
        self.ensemble_top['atom_number'] = self.ensemble_top['sb_type'].map(sbtype_idx_dict)
    
    def convert_topology(self, ego_native):
        '''
        This functions is needed to convert the structure based atomtypes from a force field to gromos.
        It is tested using charmm were the only different atomtypes are OT1 and OT2 which has to be renamed to O1 and O2.
        Other differences are on the atom index which is solved using the structure based atomtype.
        Here a dictionary is made by charmm key: gromos value.
        '''
        multiego_topology = ego_native.ensemble_top
        md_topology = self.ensemble_top

        multiego_atoms = set(multiego_topology['atom'].to_list())
        md_atoms = set(md_topology['atom'].to_list())
        diff_atoms = list(multiego_atoms - md_atoms)
        
        merged_atoms = pd.DataFrame()
        merged_atoms['atoms_multiego'] = multiego_topology['atom']
        merged_atoms['multiego_resnum'] = multiego_topology['residue_number']
        merged_atoms['atoms_md'] = md_topology['atom']
        merged_atoms['md_resnum'] = md_topology['residue_number']
        merged_atoms = merged_atoms.loc[merged_atoms['atoms_multiego'].isin(diff_atoms)]
        merged_atoms['sb_multiego'] = merged_atoms['atoms_multiego']+'_'+merged_atoms['multiego_resnum'].astype(str)
        merged_atoms['sb_md'] = merged_atoms['atoms_md']+'_'+merged_atoms['md_resnum'].astype(str)
        merged_atoms_dict = merged_atoms.set_index('sb_md')['sb_multiego'].to_dict()

        md_topology = md_topology.replace({'sb_type':merged_atoms_dict})
        self.ensemble_top = md_topology
        updated_mat_plainMD = self.atomic_mat_MD
        updated_mat_plainMD = updated_mat_plainMD.replace({'ai':merged_atoms_dict})
        updated_mat_plainMD = updated_mat_plainMD.replace({'aj':merged_atoms_dict})
        self.atomic_mat_MD = updated_mat_plainMD
        self.conversion_dict = merged_atoms_dict


    def add_random_coil(self):
        # The random coil should come from the same native ensemble
        #if not ensemble_parameters['not_matching_native']:
        atomic_mat_random_coil = random_coil_mdmat(self.ensemble_parameters[f'{self.name}_contacts'], self.idx_sbtype_dict)
        self.atomic_mat_random_coil = atomic_mat_random_coil
        
        
    def add_MD_contacts(self):
        # MD_contacts
        atomic_mat_MD = plainMD_mdmat(self.parameters, self.ensemble_parameters[f'{self.name}_contacts'], self.idx_sbtype_dict, self.idx_chain_dict)
        self.atomic_mat_MD = atomic_mat_MD
    

    def get_structure_pairs(self, ego_native):
        print('\t- Reading pdb structure for pairs')
        mda_structure = mda.Universe(self.ensemble_parameters['structure_file'], guess_bonds = False)#, topology_format='PDB')
        print('\t- Making pairs')
        structure_pairs = PDB_LJ_pairs(mda_structure, ego_native.atomic_mat_random_coil, self.native_atomtypes, self.parameters)
        self.structure_pairs = structure_pairs


    def get_ligand_ensemble(self): # TODO change name
        '''
        Reading ligand .itp and .prm to get topology parameters to add in topol_ligand and ffnonbonded.itp.
        Parameters are ligand C6 and C12, bonds, angles, dihedrals and pairs.
        '''
        # ATOMS
        # Here is just filtering by the ligand 
        ligand_residue_number = self.ensemble_top['residue_number'].max()
        self.ligand_residue_number = ligand_residue_number

        # extra atomtypes for c12 definitions
        print('\t - Retrieving ligand extra atom definitions')
        itp = read_topology(self.ensemble_parameters['itp_file'])
        prm = read_topology(self.ensemble_parameters['prm_file'])
        extra_ligand_top = extra_topology_ligands(itp, prm, ligand_residue_number)

        self.ligand_moleculetype = extra_ligand_top.ligand_moleculetype

        # Inserting the new c12 in ffnonbonded.itp
        ligand_ensemble_top = self.ensemble_top.loc[self.ensemble_top['residue_number'] == ligand_residue_number]
        ligand_ensemble_top['c12'] = ligand_ensemble_top['sb_type'].map(extra_ligand_top.ligand_sbtype_c12_dict)
        ligand_ensemble_top['atom_number'] = ligand_ensemble_top['sb_type'].map(extra_ligand_top.sbtype_ligand_number_dict)
        #ligand_ensemble_top['c12'] = ligand_ensemble_top['c12'].map(lambda x:'{:.6e}'.format(x))
        self.ensemble_top = ligand_ensemble_top
        
        ligand_sbtype_number_dict = ligand_ensemble_top[['sb_type', 'atom_number']].copy()
        ligand_sbtype_number_dict = ligand_sbtype_number_dict.set_index('sb_type')['atom_number'].to_dict()   
        self.ligand_sbtype_number_dict = ligand_sbtype_number_dict

        update_ligand_bonds = extra_ligand_top.ligand_bonds
        update_ligand_bonds['ai'] = update_ligand_bonds['ai'].map(ligand_sbtype_number_dict)
        update_ligand_bonds['aj'] = update_ligand_bonds['aj'].map(ligand_sbtype_number_dict)
        update_ligand_bonds.dropna(inplace=True)
        update_ligand_bonds['ai'] = update_ligand_bonds['ai'].astype(int)
        update_ligand_bonds['aj'] = update_ligand_bonds['aj'].astype(int)
        # This is for gromacs which is bitchy
        update_ligand_bonds['c1'] = update_ligand_bonds['c1']/self.parameters['ligand_reduction']
        self.ligand_bonds = update_ligand_bonds
        bond_pairs = list([(str(ai), str(aj)) for ai, aj in zip(update_ligand_bonds['ai'].to_list(), update_ligand_bonds['aj'].to_list())])
        self.ligand_pair_bonds = bond_pairs

        update_ligand_angles = extra_ligand_top.ligand_angles
        update_ligand_angles['ai'] = update_ligand_angles['ai'].map(ligand_sbtype_number_dict)
        update_ligand_angles['aj'] = update_ligand_angles['aj'].map(ligand_sbtype_number_dict)
        update_ligand_angles['ak'] = update_ligand_angles['ak'].map(ligand_sbtype_number_dict)
        update_ligand_angles.dropna(inplace=True)
        update_ligand_angles['ai'] = update_ligand_angles['ai'].astype(int)
        update_ligand_angles['aj'] = update_ligand_angles['aj'].astype(int)
        update_ligand_angles['ak'] = update_ligand_angles['ak'].astype(int)
        self.ligand_angles = update_ligand_angles

        update_ligand_dihedrals = extra_ligand_top.ligand_dihedrals
        update_ligand_dihedrals['ai'] = update_ligand_dihedrals['ai'].map(ligand_sbtype_number_dict)
        update_ligand_dihedrals['aj'] = update_ligand_dihedrals['aj'].map(ligand_sbtype_number_dict)
        update_ligand_dihedrals['ak'] = update_ligand_dihedrals['ak'].map(ligand_sbtype_number_dict)
        update_ligand_dihedrals['al'] = update_ligand_dihedrals['al'].map(ligand_sbtype_number_dict)
        update_ligand_dihedrals.dropna(inplace=True)
        update_ligand_dihedrals['ai'] = update_ligand_dihedrals['ai'].astype(int)
        update_ligand_dihedrals['aj'] = update_ligand_dihedrals['aj'].astype(int)
        update_ligand_dihedrals['ak'] = update_ligand_dihedrals['ak'].astype(int)
        update_ligand_dihedrals['al'] = update_ligand_dihedrals['al'].astype(int)
        self.ligand_dihedrals = update_ligand_dihedrals

        # This is used when when want to read ligand pairs from the original topology
        # We might want to remove this part
        update_ligand_pairs = extra_ligand_top.ligand_pairs
        update_ligand_pairs['ai'] = update_ligand_pairs['ai'].map(ligand_sbtype_number_dict)
        update_ligand_pairs['aj'] = update_ligand_pairs['aj'].map(ligand_sbtype_number_dict)
        update_ligand_pairs.dropna(inplace=True)
        update_ligand_pairs['ai'] = update_ligand_pairs['ai'].astype(int)
        update_ligand_pairs['aj'] = update_ligand_pairs['aj'].astype(int)
        self.ligand_pairs = update_ligand_pairs
     

    def ligand_MD_LJ_pairs(self):
        # TODO this one will be moved in multiego_ensemble
        print('\t- Adding the ligand LJ potential')

        # Following the idea that the ligand is considered as a residue in the same chain,
        # we select ligand pairs by selecting the spare residue compared with the ligand
        atomic_ligand_mat = self.atomic_mat_MD
        # Drop values below md_treshold, otherwise the epsilon will be negative
        atomic_ligand_mat.drop(atomic_ligand_mat[atomic_ligand_mat['probability'] < self.parameters['md_threshold']].index, inplace=True)
        #atomic_ligand_mat.drop(atomic_ligand_mat[atomic_ligand_mat['probability'] <= 0].index, inplace=True)
        # Filtering for the ligand
        #atomic_ligand_mat.dropna(inplace=True)
        atomic_ligand_mat = atomic_ligand_mat.loc[(atomic_ligand_mat['residue_ai'] == self.ligand_residue_number) | (atomic_ligand_mat['residue_aj'] == self.ligand_residue_number)]
        self_interactions = atomic_ligand_mat.loc[(atomic_ligand_mat['residue_ai'] == self.ligand_residue_number) & (atomic_ligand_mat['residue_aj'] == self.ligand_residue_number)]
        
        # TODO to be fixed. Here I am removing the self contacts of the ligand which with the latest updates causes the molecules to overlap.
        # Namely, with the new update more self ligand contacts are retained with a very high probability.
        # A quick and dirty fix is to remove such self contacts, but those should be added in pairs and exclusions properly.
        mask = ((atomic_ligand_mat['residue_ai'] == self.ligand_residue_number) & (atomic_ligand_mat['residue_aj'] == self.ligand_residue_number))
        #print(atomic_ligand_mat[mask].to_string())
        atomic_ligand_mat = atomic_ligand_mat[~mask]

        atomic_ligand_mat['sigma'] = (atomic_ligand_mat['distance']) / (2**(1/6))
        atomic_ligand_mat[['idx_ai', 'idx_aj']] = atomic_ligand_mat[['ai', 'aj']]
        atomic_ligand_mat.set_index(['idx_ai', 'idx_aj'], inplace = True)
        
        # We are using the old equation (prior to the RC version)
        atomic_ligand_mat['epsilon'] = self.parameters['epsilon_ligand']*(1-((np.log(atomic_ligand_mat['probability']))/(np.log(self.parameters['md_threshold']))))
        atomic_ligand_mat.drop(columns = ['distance', 'residue_ai', 'residue_aj', 'probability'], inplace = True)
        atomic_ligand_mat.dropna(inplace=True)
        atomic_ligand_mat = atomic_ligand_mat[atomic_ligand_mat.epsilon != 0]
        self.ligand_atomic_mat_MD = atomic_ligand_mat

# END CLASS



# TODO this one might be included in the ensemble class
def prepare_ensemble_topology(topology, structure, ensemble_parameters, parameters):
    print('\t\t- Checking the atoms in both Topology and Structure')
    for atom_top, atom_struct in zip(topology.atoms, structure.atoms):
        if str(atom_top) != str(atom_struct):
            print('- Topology and structure have different atom definitions\n\n')
            print(atom_top, atom_struct)
            exit()
    print('\t\t- Atoms between Topology and Structure are corresponding')
    
    topology_df = topology.to_dataframe()
    structure_df = structure.to_dataframe()

    # Removing solvent from the dataframe
    topology_df.drop(topology_df[topology_df.resname == 'SOL'].index, inplace=True) 
    print('\t\t- Generating multi-eGO topology')
    multiego_top = pd.DataFrame()
    multiego_top['atom_number'] = structure_df['number']
    multiego_top['atom_type'] = topology_df['type']
    multiego_top['residue_number'] = structure_df['resnum']
    multiego_top['residue'] = structure_df['resname']
    multiego_top['atom'] = topology_df['name']
    multiego_top['cgnr'] = structure_df['resnum']
    multiego_top['mass'] = topology_df['mass']
    multiego_top['atomic_number'] = topology_df['atomic_number']
    #multiego_top['chain'] = chain_ids
    multiego_top['chain'] = structure_df['chain']
    multiego_top['charge'] = '0.000000'
    multiego_top['ptype'] = 'A'
    multiego_top['c6'] = '0.00000e+00'
    multiego_top['c12'] = multiego_top['atom_type'].map(gromos_atp['c12'])

    #if ensemble_parameters['is_MD'] == True:
    print('\t\t- Removing Hydrogens')
    # MD has hydrogen which we don't use
    hydrogen = topology['@H=']
    hydrogen_number = len(hydrogen.atoms)
    hydrogen_namelist = []
    for h in hydrogen.atoms:
        hydrogen_namelist.append(h.name)
    hydrogen_namelist = list(set(hydrogen_namelist))
    # Multi-eGO topology
    mask = (multiego_top['atom']).isin(hydrogen_namelist)
    multiego_top = multiego_top[~mask]
    multiego_top.reset_index(inplace=True)
    multiego_top['atom_number'] = multiego_top.index+1

    print('\t\t- Topology fixes')
    # Removing an extra H to PRO
    pd.options.mode.chained_assignment = None 

    mask = ((multiego_top['residue'] == "PRO") & (multiego_top['atom_type'] == 'N'))
    multiego_top['mass'][mask] = multiego_top['mass'][mask].astype(float).sub(1)
    # Adding an extra H to the N terminal
    mask = ((multiego_top['residue_number'] == multiego_top['residue_number'].min()) & (multiego_top['atom_type'] == 'N'))
    multiego_top['mass'][mask] = multiego_top['mass'][mask].astype(float).add(2)

    # Aromatic carbons dictionary
    aromatic_carbons_dict = {
        'PHE': ['CD1', 'CD2', 'CE1', 'CE2', 'CZ'],
        'TYR': ['CD1', 'CD2', 'CE1', 'CE2'],
        'HIS': ['CE1', 'CD2'],
        'TRP': ['CD1', 'CE3', 'CZ2', 'CZ3', 'CH2']
    }

    for resname, atomnames in aromatic_carbons_dict.items():
        for atom in atomnames:
            mask = ((multiego_top['residue'] == resname) & (multiego_top['atom'] == atom))
            multiego_top['mass'][mask] = multiego_top['mass'][mask].astype(float).add(1)

    print('\t\t- Defining multi-eGO atomtypes')
    multiego_top['sb_type'] = multiego_top['atom'] + '_' + multiego_top['residue_number'].astype(str)

    return multiego_top


# TODO this one might be included in the ensemble class
def sb_type_conversion(multiego_ensemble, md_ensemble):
    '''
    This functions is needed to convert the structure based atomtypes from a force field to gromos.
    It is tested using charmm were the only different atomtypes are OT1 and OT2 which has to be renamed to O1 and O2.
    Other differences are on the atom index which is solved using the structure based atomtype.
    Here a dictionary is made by charmm key: gromos value.
    '''

    multiego_topology = multiego_ensemble.multiego_topology
    md_topology = md_ensemble.multiego_topology

    convert_dict = {}
    multiego_atoms = set(multiego_topology['atom'].to_list())
    md_atoms = set(md_topology['atom'].to_list())
    diff_atoms = list(multiego_atoms - md_atoms)
    merged_atoms = pd.DataFrame()
    merged_atoms['atoms_multiego'] = multiego_topology['atom']
    merged_atoms['multiego_resnum'] = multiego_topology['residue_number']
    merged_atoms['atoms_md'] = md_topology['atom']
    merged_atoms['md_resnum'] = md_topology['residue_number']
    merged_atoms = merged_atoms.loc[merged_atoms['atoms_multiego'].isin(diff_atoms)]
    merged_atoms['sb_multiego'] = merged_atoms['atoms_multiego']+'_'+merged_atoms['multiego_resnum'].astype(str)
    merged_atoms['sb_md'] = merged_atoms['atoms_md']+'_'+merged_atoms['md_resnum'].astype(str)
    merged_atoms_dict = merged_atoms.set_index('sb_md')['sb_multiego'].to_dict()
    
    updated_mat_plainMD = md_ensemble.atomic_mat_plainMD
    updated_mat_plainMD = updated_mat_plainMD.replace({'ai':merged_atoms_dict})
    updated_mat_plainMD = updated_mat_plainMD.replace({'aj':merged_atoms_dict})

    return updated_mat_plainMD, merged_atoms_dict


def PDB_LJ_pairs(structure_pdb, atomic_mat_random_coil, atomtypes, parameters):
    '''
    This function measures all the distances between all atoms using MDAnalysis.
    It works on both native and fibril in the same manner.
    Pairs are filtered based on the distance_cutoff which is fixed at 5.5A (in main parameters).
    A second filter is based on the distance_residue. Pairs between atoms closer than two residues are removed 
    if the contact is in the same chain.
    The function also provides the sigma and the epsilon of each pair.
    In case of intramolecular contacts, pairs are reweighted based on the random_coil probability
    '''
    print('\tAddition of PDB derived native LJ-pairs')

    print('\t\tMeasuring distances between all atom in the structure')
    # Selecting all atoms in the system
    atom_sel = structure_pdb.select_atoms('all')

    # Calculating all the distances between atoms.
    # The output is a combination array.
    self_distances = distances.self_distance_array(atom_sel.positions)
    print('\t\tNumber of distances measured :', len(self_distances))
    
    # The MDAnalysis contains only distances, so we rebuilt atom pairs in the same manner
    # using the atomtypes list of native and fibril which will match with the distance array.

    # TODO create directly the two separated lists
    pairs_list = list(itertools.combinations(atomtypes, 2))

    # But the combinations are list of list and we need to separate them.
    pairs_ai, pairs_aj = [], []
    for n in range(0, len(pairs_list)):
        i = pairs_list[n][0]
        pairs_ai.append(i)
        j = pairs_list[n][1]
        pairs_aj.append(j)

    # Creation of the dataframe containing the atom pairs and the distances.
    # Also, it will be prepared for sigma and epsilon.
    structural_LJ = pd.DataFrame(columns = ['ai', 'aj', 'distance', 'sigma', 'epsilon'])
    structural_LJ['ai'] = pairs_ai
    structural_LJ['aj'] = pairs_aj
    structural_LJ['distance'] = self_distances
    print('\t\tRaw pairs list ', len(structural_LJ))
    
    # Keep only the atoms within cutoff
    structural_LJ = structural_LJ[structural_LJ.distance < parameters["distance_cutoff"]] # PROTEIN CONFIGURATION
    print(f'\t\tPairs below cutoff {parameters["distance_cutoff"]}: ', len(structural_LJ))

    # That is name_resname:resid made from the previous function.
    # Extracting the resid information to check if the atom pair is on the same chain.
    structural_LJ[['ai', 'chain_ai']] = structural_LJ.ai.str.split(":", expand = True)
    structural_LJ[['aj', 'chain_aj']] = structural_LJ.aj.str.split(":", expand = True)
    structural_LJ['same_chain'] = np.where(structural_LJ['chain_ai'] == structural_LJ['chain_aj'], 'Yes', 'No')
    print('\t\tPairs within the same chain: ', len(structural_LJ.loc[structural_LJ['same_chain'] == 'Yes']))
    print('\t\tPairs not in the same chain: ', len(structural_LJ.loc[structural_LJ['same_chain'] == 'No']))

    # if two pairs are made by aminoacids closer than X they'll be deleted. 
    structural_LJ[['type_ai', 'resnum_ai']] = structural_LJ.ai.str.split("_", expand = True)
    structural_LJ[['type_aj', 'resnum_aj']] = structural_LJ.aj.str.split("_", expand = True)
    # And to do that it is necessary to convert the two columns into integer
    structural_LJ = structural_LJ.astype({"resnum_ai": int, "resnum_aj": int})
    structural_LJ['diffr'] = abs(structural_LJ['resnum_aj'] - structural_LJ['resnum_ai'])
    structural_LJ.drop(columns = ['chain_ai', 'chain_aj', 'resnum_ai', 'resnum_aj'], inplace = True) 
    structural_LJ.drop(structural_LJ[(structural_LJ['diffr'] < parameters['distance_residue']) & (structural_LJ['same_chain'] == 'Yes')].index, inplace = True)    
    
    # Inverse pairs calvario
    # this must list ALL COLUMNS!
    inv_LJ = structural_LJ[['aj', 'ai', 'distance', 'sigma', 'epsilon', 'same_chain', 'type_ai', 'type_aj', 'diffr']].copy()
    inv_LJ.columns = ['ai', 'aj', 'distance', 'sigma', 'epsilon', 'same_chain', 'type_ai', 'type_aj', 'diffr']
    structural_LJ = pd.concat([structural_LJ, inv_LJ], axis=0, sort = False, ignore_index = True)
    structural_LJ['sigma'] = (structural_LJ['distance']/10) / (2**(1/6))

    inter_LJ = structural_LJ.loc[structural_LJ['same_chain']=='No']
    intra_LJ = structural_LJ.loc[structural_LJ['same_chain']=='Yes']

    # Here we sort all the atom pairs based on the distance and we keep the closer ones, prioritising intermolecular contacts.
    # Sorting the pairs
    inter_LJ.sort_values(by = ['ai', 'aj', 'distance'], ascending = [True, True, True], inplace = True)
    # Cleaning the duplicates
    inter_LJ = inter_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # Removing the reverse duplicates
    cols = ['ai', 'aj']
    inter_LJ[cols] = np.sort(inter_LJ[cols].values, axis=1)
    inter_LJ = inter_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    inter_LJ[['idx_ai', 'idx_aj']] = inter_LJ[['ai', 'aj']]
    inter_LJ.set_index(['idx_ai', 'idx_aj'], inplace=True)
    
    # Here we sort all the atom pairs based on the distance and we keep the closer ones, prioritising intramolecular contacts.
    # Sorting the pairs
    intra_LJ.sort_values(by = ['ai', 'aj', 'distance'], ascending = [True, True, True], inplace = True)
    # Cleaning the duplicates
    intra_LJ = intra_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # Removing the reverse duplicates
    cols = ['ai', 'aj']
    intra_LJ[cols] = np.sort(intra_LJ[cols].values, axis=1)
    intra_LJ = intra_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    intra_LJ[['idx_ai', 'idx_aj']] = intra_LJ[['ai', 'aj']]
    intra_LJ.set_index(['idx_ai', 'idx_aj'], inplace=True)

    atomic_mat_random_coil[['idx_ai', 'idx_aj']] = atomic_mat_random_coil[['rc_ai', 'rc_aj']]
    atomic_mat_random_coil.set_index(['idx_ai', 'idx_aj'], inplace = True)
    inter_LJ = pd.concat([inter_LJ, atomic_mat_random_coil], axis=1, join='inner')
    intra_LJ = pd.concat([intra_LJ, atomic_mat_random_coil], axis=1, join='inner')

    structural_LJ = pd.concat([inter_LJ, intra_LJ], axis=0, sort = False, ignore_index = True)

    print(f'\t\tAll the pairs after removing duplicates: ', len(structural_LJ))

    structural_LJ['epsilon'] = parameters['epsilon_amyl']

    structural_LJ['epsilon'].loc[(structural_LJ['same_chain']=='Yes')&(structural_LJ['rc_probability']<0.999)] = -(parameters['epsilon_md']/np.log(parameters['rc_threshold']))*(np.log(0.999/np.maximum(structural_LJ['rc_probability'],parameters['rc_threshold'])))
    structural_LJ['epsilon'].loc[(structural_LJ['same_chain']=='Yes')&(structural_LJ['rc_probability']>=0.999)] = 0 
    structural_LJ['epsilon'].loc[(structural_LJ['same_chain']=='Yes')&(structural_LJ['epsilon'] < 0.01*parameters['epsilon_md'])] = 0
    structural_LJ.dropna(inplace=True)
    structural_LJ = structural_LJ[structural_LJ.epsilon != 0]
    structural_LJ['source'] = 'PDB'

    print('\t\tSigma and epsilon completed ', len(structural_LJ))
    structural_LJ.drop(columns = ['distance', 'type_ai', 'type_aj', 'rc_ai',  'rc_aj',  'rc_distance', 'rc_residue_ai', 'rc_residue_aj', 'diffr'], inplace = True)

    return structural_LJ


def MD_LJ_pairs(atomic_mat_plainMD, atomic_mat_random_coil, parameters, name):
    '''
    This function reads the probabilities obtained using mdmat on the plainMD and the random coil simulations.
    For each atom contact the sigma and epsilon are obtained.
    '''
    print('\t- Addition of MD derived LJ-pairs')

    atomic_mat_plainMD[['idx_ai', 'idx_aj']] = atomic_mat_plainMD[['ai', 'aj']]
    atomic_mat_plainMD.set_index(['idx_ai', 'idx_aj'], inplace = True)

    atomic_mat_random_coil[['idx_ai', 'idx_aj']] = atomic_mat_random_coil[['rc_ai', 'rc_aj']]
    atomic_mat_random_coil.set_index(['idx_ai', 'idx_aj'], inplace = True)

    intra_mat_probability = pd.DataFrame()
    inter_mat_probability = pd.DataFrame()

    # TODO define based the command in input
    # TODO define functions based on the choise of inter-intra parametrisation
    
    if parameters['egos'] == 'all':
        print('\t- egos = all. Intra and inter molecular contacts will be learned from all the ensembles')
        # Retrieving the intramolecular contacts
        intra_atomic_mat_plainMD = atomic_mat_plainMD.loc[atomic_mat_plainMD['same_chain'] == 'Yes']
        inter_atomic_mat_plainMD = atomic_mat_plainMD.loc[atomic_mat_plainMD['same_chain'] == 'No']
        
        intra_mat_probability = reweight_intramolecular_contacts(intra_atomic_mat_plainMD, atomic_mat_random_coil, parameters, name)
        inter_mat_probability = reweight_intermolecular_contacts(inter_atomic_mat_plainMD, atomic_mat_random_coil, parameters, name)


    elif parameters['egos'] == 'split':
        # It is similar as egos=all but the contacts are obtained from separate ensembles
        if name == parameters['intra']:
            print('\t\t- Intramolecular contacts handling')
            # This one uses Paissoni Equation 2.1 with the random coil
            intra_atomic_mat_plainMD = atomic_mat_plainMD.loc[atomic_mat_plainMD['same_chain'] == 'Yes']
            intra_mat_probability = reweight_intramolecular_contacts(intra_atomic_mat_plainMD, atomic_mat_random_coil, parameters, name)

        if name == parameters['inter']:
            print('\t\t- Intermolecular contacts handling')
            # This one uses Paissoni Equation 1.0 without the random coil (still supplied in the function input for reasons)
            inter_atomic_mat_plainMD = atomic_mat_plainMD.loc[atomic_mat_plainMD['same_chain'] == 'No']
            inter_mat_probability = reweight_intermolecular_contacts(inter_atomic_mat_plainMD, atomic_mat_random_coil, parameters, name)

    else:
        print("egos is not either 'all' or 'split")
        exit()

    atomic_mat_merged = pd.concat([intra_mat_probability, inter_mat_probability], axis=0, sort = False, ignore_index = True)

    return atomic_mat_merged


def reweight_intramolecular_contacts(atomic_mat_plainMD, atomic_mat_random_coil, parameters, name):
    
    #intra_mat_probability = atomic_mat_plainMD[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"])
    #for coso1, coso2 in intra_mat_probability:
    #    #print(coso1)
    #    #print(coso2)
    #    fig = px.histogram(coso2, nbins=50)
    #    fig.write_html(f'plots/intra_plots_{coso1}.html')


    #intra_mat_probability = atomic_mat_plainMD[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"]).agg({np.min,np.max})

    # DISTANZA MINIMA E PROBABILITà MEDIA == distanza minima una migliore geometria però si sballano le probabilità

    # Here we are taking the minimum value of distance and the consequent standard deviation
    intra_mat_distance_std = atomic_mat_plainMD['distance'].groupby(by=["idx_ai", "idx_aj"]).agg(['min', 'std'])
    intra_mat_distance_std.columns = ['distance_min', 'distance_std']
    # Here I replace NaN with 0 otherwise we loose all the contacts represented once in the case of a single chain of the ensemble.
    # 0 will allow to keep the distance cutoff the same as the minimum distance
    # If the contacts is still low represented, other filters are applied later.
    intra_mat_distance_std['distance_std'] = intra_mat_distance_std['distance_std'].fillna(0)

    intra_mat_distance_std['distance_cutoff'] = intra_mat_distance_std['distance_min'] + intra_mat_distance_std['distance_std']
    intra_mat_probability = pd.concat([atomic_mat_plainMD, intra_mat_distance_std], axis=1)
    intra_mat_probability = intra_mat_probability.loc[intra_mat_probability['distance'] <= intra_mat_probability['distance_cutoff']]


    #print(inter_mat_probability.loc[(inter_mat_probability['ai'] == 'CA_1') & (inter_mat_probability['aj'] == 'CB_1')].to_string())
    intra_mat_probability_count = intra_mat_probability['probability'].groupby(by=['idx_ai', 'idx_aj']).count()
    #print(inter_mat_probability_count)
    intra_mat_probability_wmean = intra_mat_probability['probability'].groupby(by=['idx_ai', 'idx_aj']).prod()
    #print(inter_mat_probability_wmean)
    probability_reweighted = pd.concat([intra_mat_probability_wmean, intra_mat_probability_count], axis=1)
    probability_reweighted.columns = ['product', 'count']
    probability_reweighted['reweight'] = probability_reweighted['product'] ** (1/probability_reweighted['count'])
    #print(probability_reweighted)


    # MEDIE PER OGNI CONTATTO

    #intra_atomic_mat_plainMD = atomic_mat_plainMD.loc[atomic_mat_plainMD['same_chain'] == 'Yes']
    #intra_mat_probability = atomic_mat_plainMD[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"]).agg({'std', 'std'})
    #intra_mat_probability = atomic_mat_plainMD[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"]).agg(['min', 'mean', 'std'])

    intra_mat_probability = intra_mat_probability[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"]).agg(['min', 'mean', 'std'])

    #intra_mat_probability.columns = ['probability', 'distance']

    # FLAG MINS MEANS

    intra_mat_probability.columns = ['probability_min', 'probability', 'probability_std', 'distance_min', 'distance_mean', 'distance_std']
    #intra_mat_probability.columns = ['probability_min', 'probability', 'probability_std', 'distance_min', 'distance', 'distance_std']
    
    
    intra_mat_probability['probability_std'] = intra_mat_probability['probability_std'].fillna(0)
    intra_mat_probability['distance_std'] = intra_mat_probability['distance_std'].fillna(0)
    intra_mat_probability['probability_reweighted'] = probability_reweighted['reweight']
    intra_mat_probability = intra_mat_probability[['probability_min', 'probability', 'probability_reweighted', 'probability_std', 'distance_min', 'distance_mean', 'distance_std']]

    intra_mat_probability = pd.concat([intra_mat_probability, atomic_mat_random_coil], axis=1)
    #intra_mat_probability.columns = ['probability',  'distance',  'residue_ai', 'rc_ai',  'residue_aj',  'rc_aj',  'rc_distance',  'rc_probability']
    
    # FLAG MINS MEANS
    intra_mat_probability.columns = ['probability_min', 'probability_mean', 'probability', 'probability_std' , 'distance_min', 'distance_mean', 'distance_std', 'residue_ai', 'rc_ai',  'residue_aj',  'rc_aj',  'rc_distance',  'rc_probability']
    #intra_mat_probability.columns = ['probability_min', 'probability', 'probability_std', 'distance', 'distance_mean', 'distance_std', 'residue_ai', 'rc_ai',  'residue_aj',  'rc_aj',  'rc_distance',  'rc_probability']
    #intra_mat_probability.columns = ['probability_min', 'probability', 'probability_std', 'distance_min', 'distance', 'distance_std', 'residue_ai', 'rc_ai',  'residue_aj',  'rc_aj',  'rc_distance',  'rc_probability']
    


    intra_mat_probability.drop(columns = ['rc_ai', 'rc_aj'], inplace=True)
    intra_mat_probability['same_chain'] = 'Yes'

    # DROP DEI DUPLICATI IN BASE ALLA DISTANZA

    #intra_mat_probability = atomic_mat_plainMD.copy()
    #intra_mat_probability.drop(intra_mat_probability[intra_mat_probability['distance'] == 0].index, inplace=True)
    ## Sorting the pairs
    #intra_mat_probability.sort_values(by = ['ai', 'aj', 'distance'], inplace = True)
    ## Cleaning the duplicates
    #intra_mat_probability = intra_mat_probability.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    #intra_mat_probability = pd.concat([intra_mat_probability, atomic_mat_random_coil], axis=1)






    # Add sigma, add epsilon reweighted, add c6 and c12
    intra_mat_probability['sigma'] = (intra_mat_probability['distance_mean']) / (2**(1/6))
    # Epsilon reweight based on probability
    intra_mat_probability['epsilon'] = np.nan 
    intra_mat_probability['diffr'] = abs(intra_mat_probability['residue_aj'] - intra_mat_probability['residue_ai'])

    # Paissoni Equation 2.1
    # Attractive
    intra_mat_probability['epsilon'].loc[(intra_mat_probability['probability'] < intra_mat_probability['rc_probability'])] = 0
    intra_mat_probability['epsilon'].loc[(intra_mat_probability['probability'] >= intra_mat_probability['rc_probability'])&(intra_mat_probability['probability'] < parameters['md_threshold'])] = 0 
    intra_mat_probability['epsilon'].loc[(intra_mat_probability['probability'] >= intra_mat_probability['rc_probability'])&(intra_mat_probability['probability'] >= parameters['md_threshold'])] = -(parameters['epsilon_md']/np.log(parameters['rc_threshold']))*(np.log(intra_mat_probability['probability']/np.maximum(intra_mat_probability['rc_probability'],parameters['rc_threshold'])))
    # Repulsive
    # this is a repulsive energy of 2.49/2. kj/mol at a distance equal to sigma only for neighbour resiudes
    intra_mat_probability['epsilon'].loc[(intra_mat_probability['probability'] < intra_mat_probability['rc_probability']-parameters['md_threshold'])&(intra_mat_probability['diffr']<parameters['distance_residue'])] = -2.494339/2./4. 
    # this is a repulsive energy of 2.49/2.5 kj/mol at a distance equal to sigma only for next to neighbour resiudes
    intra_mat_probability['epsilon'].loc[(intra_mat_probability['probability'] < intra_mat_probability['rc_probability']-parameters['md_threshold'])&(intra_mat_probability['diffr']==parameters['distance_residue'])] = -2.494339/2.5/4. 

    # Treshold vari ed eventuali
    intra_mat_probability['epsilon'].loc[(intra_mat_probability['epsilon'] < 0.01*parameters['epsilon_md'])&(intra_mat_probability['epsilon']>0.)] = 0
    intra_mat_probability.dropna(inplace=True)
    intra_mat_probability = intra_mat_probability[intra_mat_probability.epsilon != 0]
    #intra_mat_probability.drop(columns = ['distance_min', 'residue_ai', 'residue_aj', 'probability', 'rc_distance', 'diffr'], inplace = True)

    print(f"\t\t- There are {len(intra_mat_probability)} intramolecular pairs interactions")

    # Retrieving the ai and aj information from the index and reindexing back again
    # TODO maybe there's a better way to do the same thing
    intra_mat_probability = intra_mat_probability.reset_index()
    intra_mat_probability[['ai', 'aj']] = intra_mat_probability[['idx_ai', 'idx_aj']]
    intra_mat_probability.set_index(['idx_ai', 'idx_aj'], inplace = True)

    # Changing the columns order to more human readable
    #intra_mat_probability = intra_mat_probability[['ai', 'aj', 'sigma', 'epsilon', 'rc_probability', 'same_chain']]
    intra_mat_probability = intra_mat_probability[['ai', 'aj', 'sigma', 'epsilon', 'rc_probability', 'same_chain', 'probability_std', 'distance_std']]


    # Inverse pairs calvario
    # this must list ALL COLUMNS!
    inv_LJ = intra_mat_probability[['aj', 'ai', 'sigma', 'epsilon', 'rc_probability', 'same_chain', 'probability_std', 'distance_std']].copy()
    inv_LJ.columns = ['ai', 'aj', 'sigma', 'epsilon', 'rc_probability', 'same_chain', 'probability_std', 'distance_std']
    intra_mat_probability = pd.concat([intra_mat_probability, inv_LJ], axis=0, sort = False, ignore_index = True)
    # Here we sort all the atom pairs based on the distance and we keep the closer ones.
    # Sorting the pairs
    intra_mat_probability.sort_values(by = ['ai', 'aj', 'sigma'], inplace = True)
    # Cleaning the duplicates
    intra_mat_probability = intra_mat_probability.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # Removing the reverse duplicates
    cols = ['ai', 'aj']
    intra_mat_probability[cols] = np.sort(intra_mat_probability[cols].values, axis=1)
    intra_mat_probability = intra_mat_probability.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    intra_mat_probability[['idx_ai', 'idx_aj']] = intra_mat_probability[['ai', 'aj']]
    intra_mat_probability.set_index(['idx_ai', 'idx_aj'], inplace=True)
    intra_mat_probability['source'] = name
    print(f'\t\t- Pairs added after removing duplicates: ', len(intra_mat_probability))
    print("\t\t\t- Epsilon input:", parameters['epsilon_md']) 
    print("\t\t\t- Average intramolecular epsilon is", intra_mat_probability['epsilon'].loc[(intra_mat_probability['epsilon']>0.)].mean())
    print("\t\t\t- Maximum intramolecular epsilon is", intra_mat_probability['epsilon'].max())

    return intra_mat_probability


def reweight_intermolecular_contacts(atomic_mat_plainMD, atomic_mat_random_coil, parameters, name):

    histo = atomic_mat_plainMD[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"])
    #histo.to_csv('plots/atomic_mat_plainMD')
    #for coso1, coso2 in histo:
    #    #print(coso1)
    #    #print(coso2)
    #    fig = px.histogram(coso2, nbins=50)
    #    fig.write_html(f'plots/inter_{coso1}.html')

    #inter_mat_probability = atomic_mat_plainMD[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"]).agg({np.min,np.max})  
    #print(atomic_mat_plainMD.filter(like='OG_8', axis=0).to_string())
    #print(atomic_mat_plainMD.filter(like='O_8', axis=0).to_string())

    #exit()

    # Filtering by probability treshold
    inter_mat = atomic_mat_plainMD.copy()   

    # SEED DEBUG
    inter_mat.to_csv(f'analysis/inter_mat_{name}')


    print('first',len(inter_mat))
    #inter_mat.drop(inter_mat[inter_mat['probability'] < parameters['md_threshold']].index, inplace=True)
    #inter_mat = inter_mat[inter_mat['probability'] > parameters['md_threshold']]
    
    # SCAMUFFOH
    #inter_mat = inter_mat[inter_mat['probability'] > 0.5]

    print('tresh filter',len(inter_mat))

    #histo = inter_mat[['probability', 'distance']].groupby(by=["idx_ai", "idx_aj"])
    
    # SEED DEBUG
    inter_mat.to_csv(f'analysis/inter_mat_mdtreshold_{name}')
    #for coso1, coso2 in histo:
    #    #print(coso1)
    #    #print(coso2)
    #    fig = px.histogram(coso2, nbins=50)
    #    fig.write_html(f'plots2/inter_{coso1}.html')



    # STANDARD DEVIATIONS AND TRESHOLDS COMPUTED PAIRWISE
    # Select the first histogram peak based on minimum distance plus standard deviation (to be improved)
    inter_mat_distance_std = inter_mat['distance'].groupby(by=['idx_ai', 'idx_aj']).agg(['median', 'std'])
    inter_mat_distance_std.columns = ['distance_median', 'distance_std']
    inter_mat_distance_std['distance_std'] = inter_mat_distance_std['distance_std'].fillna(0)

    # TODO std delle probabilita'
    # TODO printa tutto l'elenco in ordine di std in crescita

    #inter_mat_probability_std = inter_mat['probability'].groupby(by=['idx_ai', 'idx_aj']).agg(['min', 'max', 'median', 'std'])
    #inter_mat_probability_std.columns = ['probability_min', 'probability_max', 'probability_median', 'probability_std']
    #inter_mat_probability_std['probability_std'] = inter_mat_probability_std['probability_std'].fillna(0)
    #inter_mat_probability_std.sort_values(by=['probability_std'], inplace=True)
    ##print(inter_mat_probability_std.to_string())
    





    # SEED DEBUG
    #inter_mat_probability_std.to_csv(f'analysis/probability_std_{name}')
    
    pairs_mono_inter_mat_distance_std = inter_mat_distance_std.loc[inter_mat_distance_std['distance_std'] < 0.025]
    pairs_bi_inter_mat_distance_std = inter_mat_distance_std.loc[inter_mat_distance_std['distance_std'] >= 0.025]

    #mono_distance_reweighted = pd.DataFrame()
    #for pair, data in tqdm(pairs_mono_inter_mat_distance_std.groupby(by=['idx_ai', 'idx_aj'])):
    #    # Here we take the mean for each pairs with a low std = monomodal
    #    # Distance cutoff
    #    pair_subset = inter_mat.loc[(inter_mat['ai'] == pair[0]) & (inter_mat['aj'] == pair[1])]
    #    distance_mean = pair_subset['distance'].mean()
    #    low_dist = distance_mean - data['distance_std'][0]
    #    high_dist = distance_mean + data['distance_std'][0]
    #    pair_subset = pair_subset.loc[(pair_subset['distance'] >= low_dist) & (pair_subset['distance'] <= high_dist)]
    #    mono_distance_reweighted = pd.concat([mono_distance_reweighted, pair_subset], axis=0)
    #
    ## SEED DEBUG
    #mono_distance_reweighted.to_csv(f'analysis/mono_mat_{name}')
    # SEED DEBUG
    dump_second_peak = pd.DataFrame()
    




    bi_distance_reweighted = pd.DataFrame()
    for pair, data in tqdm(pairs_bi_inter_mat_distance_std.groupby(by=['idx_ai', 'idx_aj'])):
    
        # Here we take the min+std for bimodals
        # Distance cutoff
        pair_subset = inter_mat.loc[(inter_mat['ai'] == pair[0]) & (inter_mat['aj'] == pair[1])]
        distance_cutoff = data['distance_median']




        # SEED DEBUG
        temp_dump = pair_subset.loc[pair_subset['distance'] > distance_cutoff[0]]
        dump_second_peak = pd.concat([dump_second_peak, temp_dump], axis=0)



        pair_subset = pair_subset.loc[pair_subset['distance'] <= distance_cutoff[0]]
        # PICCO SELEZIONATO
        bi_distance_reweighted = pd.concat([bi_distance_reweighted, pair_subset], axis=0)


    # Filter by the frustration of the probability:
    # Qui prendiamo la std e la aggiungiamo ai minimi e ai massimi.
    # Si ricalcola la std e se uno dei due riduce la propria std ulteriormente allora abbiamo preso un picco
    # Altrimenti e' un contatto molto rumoroso e frustrato e dunque lo buttiamo via
    # Molti dei mono possono essere un po' rumorosi ma hanno delle distanze ben definite, provo direttamente con i bi

    probability_bi_std = bi_distance_reweighted['probability'].groupby(by=['idx_ai', 'idx_aj']).agg(['std'])
    probability_bi_std.columns = ['probability_std']
    #print(probability_bi_std.to_string())
    probability_bi_std.sort_values(by=['probability_std'], inplace=True)
    print(probability_bi_std.to_string())
    exit()
    #probability_bi_std = probability_bi_std.loc[probability_bi_std['probability_std'] < ]

    for pair, data in tqdm(bi_distance_reweighted.groupby(by=['idx_ai', 'idx_aj'])):

        pair_subset = bi_distance_reweighted.loc[(bi_distance_reweighted['ai'] == pair[0]) & (bi_distance_reweighted['aj'] == pair[1])]
        
    
        
        probability_min_treshold = data['probability_min'] + data['probability_std']
        probability_max_treshold = data['probability_max'] - data['probability_std']
        
        #print(pair_subset.to_string())
        
        min_pair_subset = pair_subset.loc[pair_subset['probability'] < probability_min_treshold[0]]
        max_pair_subset = pair_subset.loc[pair_subset['probability'] > probability_max_treshold[0]]
        
        #print(probability_min_treshold)
        #print(min_pair_subset.to_string())

        #print(probability_max_treshold)
        #print(max_pair_subset.to_string())

        min_std2 = min_pair_subset['probability'].std()
        max_std2 = max_pair_subset['probability'].std()

        #print(min_std2, data['probability_std'][0])
        #print(max_std2, data['probability_std'][0])
        if (min_std2 >= data['probability_std'][0]/2) or (max_std2 >= data['probability_std'][0]/2):
            print(pair)
            print(min_std2, data['probability_std'][0])
            print(max_std2, data['probability_std'][0])
            exit()
        

    #    #exit()




    # SEED DEBUG
    bi_distance_reweighted.to_csv(f'analysis/bi_mat_{name}')
    dump_second_peak.to_csv(f'analysis/bi_dump_mat_{name}')
    
    
    # SPEGNIMENTO DEI BIMODALI
    #bi_distance_reweighted = pd.DataFrame()
    
    inter_mat_distance_reweighted = pd.concat([mono_distance_reweighted, bi_distance_reweighted], axis=0)
    
    # SEED DEBUG
    inter_mat_distance_reweighted.to_csv(f'analysis/inter_mat_dist_reweight_{name}')

    inter_mat_reweighted = pd.DataFrame()
    for pair, data in tqdm(inter_mat_distance_reweighted.groupby(by=['idx_ai', 'idx_aj'])):
        # Distance reweight based on probability
        dist_prob_prod_sum = (data['distance']*data['probability']).sum()
        probability_sum = data['probability'].sum()
        distance_reweighted = dist_prob_prod_sum/probability_sum

        # Geometrical mean of probability
        probability_count = data['probability'].count()
        probability_prod = data['probability'].prod()
        probability_reweighted = probability_prod ** (1/probability_count)

        temp_dict = {
            'ai' : [pair[0]],
            'aj' : [pair[1]],
            'distance' : [distance_reweighted],
            'probability' : [probability_reweighted]
        }
        
        temp_df = pd.DataFrame.from_dict(temp_dict)
        temp_df[['idx_ai', 'idx_aj']] = temp_df[['ai', 'aj']]
        temp_df.set_index(['idx_ai', 'idx_aj'], inplace = True)
        
        inter_mat_reweighted = pd.concat([inter_mat_reweighted, temp_df])
    
    print('reweight',len(inter_mat_reweighted))
    inter_mat_reweighted = pd.concat([inter_mat_reweighted, atomic_mat_random_coil], axis=1)
    
    # SEED DEBUG
    inter_mat_reweighted.to_csv(f'analysis/inter_mat_reweight_{name}')

    inter_mat_reweighted = inter_mat_reweighted[inter_mat_reweighted['probability'] > parameters['md_threshold']]
    #inter_mat_reweighted = inter_mat_reweighted[inter_mat_reweighted['probability'] > 0.5]

    # SEED DEBUG
    inter_mat_reweighted.to_csv(f'analysis/inter_mat_lasttreshold_{name}')


    inter_mat_reweighted.drop(columns = ['rc_ai', 'rc_aj'], inplace=True)
    inter_mat_reweighted['same_chain'] = 'No'

    # Add sigma, add epsilon reweighted, add c6 and c12
    inter_mat_reweighted['sigma'] = (inter_mat_reweighted['distance']) / (2**(1/6))

    # Epsilon reweight based on probability
    inter_mat_reweighted['epsilon'] = np.nan 
    
    
    # Paissoni Equation 2.1
    inter_mat_reweighted['epsilon'] = -(parameters['epsilon_amyl']/np.log(parameters['md_threshold']))*(np.log(inter_mat_reweighted['probability']/parameters['md_threshold']))
    inter_mat_reweighted.dropna(inplace=True)
    inter_mat_reweighted['epsilon'].loc[(inter_mat_reweighted['epsilon'] < 0.01*parameters['epsilon_amyl'])] = 0
    inter_mat_reweighted = inter_mat_reweighted[inter_mat_reweighted.epsilon != 0]

    print(f"\t\t- There are {len(inter_mat_reweighted)} intermolecular pairs interactions")

    # Changing the columns order
    inter_mat_reweighted = inter_mat_reweighted[['ai', 'aj', 'sigma', 'epsilon', 'rc_probability', 'same_chain']]
    

    # Inverse pairs calvario
    # this must list ALL COLUMNS!
    inv_LJ = inter_mat_reweighted[['aj', 'ai', 'sigma', 'epsilon', 'rc_probability', 'same_chain']].copy()
    inv_LJ.columns = ['ai', 'aj', 'sigma', 'epsilon', 'rc_probability', 'same_chain']
    inter_mat_reweighted = pd.concat([inter_mat_reweighted, inv_LJ], axis=0, sort = False, ignore_index = True)
    # Here we sort all the atom pairs based on the distance and we keep the closer ones.
    # Sorting the pairs
    inter_mat_reweighted.sort_values(by = ['ai', 'aj', 'sigma'], inplace = True)
    # Cleaning the duplicates
    inter_mat_reweighted = inter_mat_reweighted.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # Removing the reverse duplicates
    cols = ['ai', 'aj']
    inter_mat_reweighted[cols] = np.sort(inter_mat_reweighted[cols].values, axis=1)
    inter_mat_reweighted = inter_mat_reweighted.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    inter_mat_reweighted[['idx_ai', 'idx_aj']] = inter_mat_reweighted[['ai', 'aj']]
    inter_mat_reweighted.set_index(['idx_ai', 'idx_aj'], inplace=True)
    inter_mat_reweighted['source'] = name
    print(f'\t\t- Pairs added after removing duplicates: ', len(inter_mat_reweighted))
    print("\t\t\t- Epsilon input:", parameters['epsilon_amyl'])
    print("\t\t\t- Average intermolecular epsilon is", inter_mat_reweighted['epsilon'].loc[(inter_mat_reweighted['epsilon']>0.)].mean())
    print("\t\t\t- Maximum intermolecular epsilon is", inter_mat_reweighted['epsilon'].max())

    return inter_mat_reweighted



def merge_and_clean_LJ(greta_LJ, type_c12_dict, parameters):
    '''
    This function merges the atom contacts from native and fibril and removed eventual duplicates.
    Also, in case of missing residues in the structure, predicts the self contacts based on the contacts available.
    '''

    print('- Merging Inter and Intra molecular interactions')
    print('\t- Merged pairs list: ', len(greta_LJ))
    print('\t- Sorting and dropping all the duplicates')
    # Inverse pairs calvario
    inv_LJ = greta_LJ[['aj', 'ai', 'sigma', 'epsilon', 'same_chain', 'rc_probability', 'source', 'probability_std', 'distance_std']].copy()
    inv_LJ.columns = ['ai', 'aj', 'sigma', 'epsilon', 'same_chain', 'rc_probability', 'source', 'probability_std', 'distance_std']
    greta_LJ = pd.concat([greta_LJ, inv_LJ], axis=0, sort = False, ignore_index = True)

    # first normalise PDB intramolecular contacts
    #for param, value in self.parameters.items():
    #    if 'md_ensemble' in param:
    #ratio = greta_LJ['epsilon'].loc[(greta_LJ['source']=='fibril_MD') | greta_LJ['source']=='native_MD'].max()/parameters['epsilon_md']
    #if(ratio>0):
    #    greta_LJ['epsilon'].loc[(greta_LJ['same_chain']=='Yes')&(greta_LJ['source']=='PDB')] *= ratio


    pairs_LJ = greta_LJ.copy()
    # Greta prioritise intermolecular interactions and shorter length ones
    greta_LJ.sort_values(by = ['ai', 'aj', 'same_chain', 'sigma'], ascending = [True, True, True, True], inplace = True)
    greta_LJ = greta_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # Removing the reverse duplicates
    cols = ['ai', 'aj']
    greta_LJ[cols] = np.sort(greta_LJ[cols].values, axis=1)
    greta_LJ = greta_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    print('\t- Cleaning and Merging Complete, pairs count:', len(greta_LJ))

    # Pairs prioritise intramolecular interactions
    pairs_LJ.sort_values(by = ['ai', 'aj', 'same_chain', 'sigma'], ascending = [True, True, False, True], inplace = True)
    pairs_LJ = pairs_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    pairs_LJ[cols] = np.sort(pairs_LJ[cols].values, axis=1)
    pairs_LJ = pairs_LJ.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # where pairs_LJ is the same of greta_LJ and same_chain is yes that the line can be dropped
    # that is I want to keep lines with same_chain no or lines with same chain yes that have same_chain no in greta_LJ
    test = pd.merge(pairs_LJ, greta_LJ, how="right", on=["ai", "aj"])
    pairs_LJ = test.loc[(test['same_chain_x']=='No')|((test['same_chain_x']=='Yes')&(test['same_chain_y']=='No'))]
    pairs_LJ.drop(columns = ['sigma_y', 'epsilon_y', 'same_chain_y', 'rc_probability_y', 'source_y'], inplace = True)
    pairs_LJ.rename(columns = {'sigma_x': 'sigma', 'rc_probability_x': 'rc_probability', 'epsilon_x': 'epsilon', 'same_chain_x': 'same_chain', 'source_x': 'source'}, inplace = True)
    # now we copy the lines with negative epsilon from greta to pairs because we want repulsive interactions only intramolecularly
    pairs_LJ = pd.concat([pairs_LJ, greta_LJ.loc[greta_LJ['epsilon']<0.]], axis=0, sort=False, ignore_index = True)
    # and we remove the same lines from greta_LJ
    greta_LJ = greta_LJ[(greta_LJ['epsilon']>0.)]

    greta_LJ.insert(2, 'type', 1)
    greta_LJ.insert(3, 'c6', '')
    greta_LJ['c6'] = 4 * greta_LJ['epsilon'] * (greta_LJ['sigma'] ** 6)
    greta_LJ.insert(4, 'c12', '')
    greta_LJ['c12'] = abs(4 * greta_LJ['epsilon'] * (greta_LJ['sigma'] ** 12))

    pairs_LJ.insert(2, 'type', 1)
    pairs_LJ.insert(3, 'c6', '')
    pairs_LJ['c6'] = 4 * pairs_LJ['epsilon'] * (pairs_LJ['sigma'] ** 6)
    pairs_LJ.insert(4, 'c12', '')
    pairs_LJ['c12'] = abs(4 * pairs_LJ['epsilon'] * (pairs_LJ['sigma'] ** 12))
    # repulsive interactions have just a very large C12
    pairs_LJ['c6'].loc[(pairs_LJ['epsilon']<0.)] = 0.
    #greta_LJ['c6'].loc[(greta_LJ['epsilon']<0.)] = 0.

    # SELF INTERACTIONS
    # In the case of fibrils which are not fully modelled we add self interactions which is a feature of amyloids
    # So that the balance between native and fibril is less steep.
    print('\t- Self interactions')
    atomtypes = set(greta_LJ['ai'])
    greta_LJ['double'] = ''

    for i in atomtypes:
        # Selection of already known atoms which contacts with themself
        greta_LJ.loc[(greta_LJ['ai'] == i) & (greta_LJ['aj'] == i), 'double'] = 'True'

    # Create a subset of the main dataframe of the self interactions.
    doubles = greta_LJ.loc[(greta_LJ['double'] == 'True')]
    atp_doubles = list(doubles['ai'])
    # The list is used to obtain all the atomtypes which does not make a self interaction
    atp_notdoubles = list(set(set(atomtypes) - set(atp_doubles)))
    atp_notdoubles.sort()

    if len(atp_notdoubles) == 0:
        print('\t\tAll atoms interacts with themselves')
        
    else:
        print('\t\tThere are', len(atp_notdoubles), 'self interactions to add')
        print(atp_notdoubles)
        # From the list of atomtypes to add, a new dataframe is created to append to the main one
        pairs_toadd = pd.DataFrame(columns = ['ai', 'aj', 'type', 'c6', 'c12', 'sigma', 'epsilon'])
        pairs_toadd['ai'] = atp_notdoubles
        pairs_toadd['aj'] = atp_notdoubles
        pairs_toadd['type'] = '1'

        # Here i want to check every value for all the atom type and if they're similar
        # make an average and paste into the main dataframe
        # I am checking every doubles based on the atomtype (except the information of the residue number) and make an average of the sigma
        # since all the epsilon are equal
        atomtypes_toadd = pairs_toadd['ai'].str.split('_', n = 1, expand = True)
        atomtypes_toadd = atomtypes_toadd[0].drop_duplicates()
        atomtypes_toadd = atomtypes_toadd.to_list()
        atomtypes_toadd = [x + '_' for x in atomtypes_toadd]

        for a in atomtypes_toadd:
            # Selects the atom pairs from the double pairs 
            doubles_a = doubles.loc[(doubles['ai'].str.contains(a)) & (doubles['aj'].str.contains(a))]
            # All the epsilon are the same, therefore the average sigma will be added on the self interaction
            sigma = doubles_a['sigma']
            eps = doubles_a['epsilon']
            c12 = doubles_a['c12']
            c6 = doubles_a['c6']
            
            if len(sigma) == 1:
                # If there is only onw sigma for the averages it will be skipped
                print('\t\tOnly one self interacting pair available for {} ==> {}'.format((str(a)[:-1]), 'Skip'))
            elif len(sigma) == 0:
                # If the missing atom pairs is not represented in the strcture there are not
                # sigmas to average
                print('\t\tThere are not self interactions for {:<12} ==> {}'.format((str(a)[:-1]), 'Skip'))
            else:
                # If there are enough sigmas to make an average then it creates the missing atom pairs
                media_sigma = sigma.mean()
                sd_sigma = sigma.std()
                media_epsilon = eps.mean()
                print('\t\tThere are {:<3} {:<3} with an average Sigma of: {:>17.10f} +/- {} epsilon {}'.format((len(sigma)), (str(a)[:-1]), media_sigma, sd_sigma, media_epsilon))
                
                # Creation of new c6 and c12
                # Epsilon structure because those are self
                new_c6 = 4 * media_epsilon * (media_sigma ** 6)
                new_c12 = 4 *media_epsilon * (media_sigma ** 12)

                # In the pairs to add dataframe all those new information are inserted
                pairs_toadd.loc[(pairs_toadd['ai'].str.contains(a)) & (pairs_toadd['aj'].str.contains(a)), 'c6'] = new_c6
                pairs_toadd.loc[(pairs_toadd['ai'].str.contains(a)) & (pairs_toadd['aj'].str.contains(a)), 'c12'] = new_c12
                pairs_toadd.loc[(pairs_toadd['ai'].str.contains(a)) & (pairs_toadd['aj'].str.contains(a)), 'sigma'] = media_sigma
                pairs_toadd.loc[(pairs_toadd['ai'].str.contains(a)) & (pairs_toadd['aj'].str.contains(a)), 'epsilon'] = media_epsilon 

        pairs_toadd.dropna(inplace = True)
        # Appending the missing atom pairs to the main dataframe
        greta_LJ = pd.concat([greta_LJ,pairs_toadd], axis=0, sort = False, ignore_index = True)
        print('\t\tSelf interactions added to greta_LJ ', len(pairs_toadd))

    # Drop double, we don't need it anymore
    greta_LJ.drop(columns = ['double'], inplace = True)

    print('\t- LJ Merging completed: ', len(greta_LJ))
    print("\t\t- Average epsilon is ", greta_LJ['epsilon'].mean())
    print("\t\t- Maximum epsilon is ", greta_LJ['epsilon'].max())

    return greta_LJ, pairs_LJ


def make_pairs_exclusion_topology(ego_topology, bond_tuple, type_c12_dict, parameters, greta_merge):
    '''
    This function prepares the [ exclusion ] and [ pairs ] section to paste in topology.top
    '''
    if not greta_merge.empty:
        greta_merge = greta_merge.rename(columns = {'; ai': 'ai'})

    ego_topology['atom_number'] = ego_topology['atom_number'].astype(str)
    atnum_type_top = ego_topology[['atom_number', 'sb_type', 'residue_number', 'atom', 'atom_type', 'residue']].copy()
    atnum_type_top['residue_number'] = atnum_type_top['residue_number'].astype(int)

    # Dictionaries definitions to map values
    atnum_type_dict = atnum_type_top.set_index('sb_type')['atom_number'].to_dict()
    type_atnum_dict = atnum_type_top.set_index('atom_number')['sb_type'].to_dict()

    #TODO this should be in topology_definitions.py
    # Building the exclusion bonded list
    # exclusion_bonds are all the interactions within 3 bonds
    # p14 are specifically the interactions at exactly 3 bonds
    ex, ex14, p14, exclusion_bonds = [], [], [], []
    for atom in ego_topology['atom_number'].to_list():
        for t in bond_tuple:
            if t[0] == atom:
                first = t[1]
                ex.append(t[1])
            elif t[1] == atom:
                first = t[0]
                ex.append(t[0])
            else: continue
            for tt in bond_tuple:
                if (tt[0] == first) & (tt[1] != atom):
                    second = tt[1]
                    ex.append(tt[1])
                elif (tt[1] == first) & (tt[0] != atom):
                    second = tt[0]
                    ex.append(tt[0])
                else: continue
                for ttt in bond_tuple:
                    if (ttt[0] == second) & (ttt[1] != first):
                        ex.append(ttt[1])
                        ex14.append(ttt[1])

                    elif (ttt[1] == second) & (ttt[0] != first):
                        ex.append(ttt[0])
                        ex14.append(ttt[0])
        for e in ex:
            exclusion_bonds.append((str(str(atom) + '_' + str(e))))
            exclusion_bonds.append((str(str(e) + '_' + str(atom))))
        ex = []
        for e in ex14:
            p14.append((str(str(atom) + '_' + str(e))))
            p14.append((str(str(e) + '_' + str(atom))))
        ex14 = []

    if not greta_merge.empty:
        # pairs from greta does not have duplicates because these have been cleaned before
        pairs = greta_merge[['ai', 'aj', 'c6', 'c12', 'epsilon', 'same_chain', 'rc_probability', 'source']].copy()
        pairs['c12_ai'] = pairs['ai']
        pairs['c12_aj'] = pairs['aj']
        
        # The exclusion list was made based on the atom number
        pairs['ai'] = pairs['ai'].map(atnum_type_dict)
        pairs['aj'] = pairs['aj'].map(atnum_type_dict)
        pairs['check'] = pairs['ai'] + '_' + pairs['aj']
        
        # Here the drop the contacts which are already defined by GROMACS, including the eventual 1-4 exclusion defined in the LJ_pairs
        pairs['exclude'] = ''
        pairs.loc[(pairs['check'].isin(exclusion_bonds)), 'exclude'] = 'Yes' 
        mask = pairs.exclude == 'Yes'
        pairs = pairs[~mask]
        pairs['c12_ai'] = pairs['c12_ai'].map(type_c12_dict)
        pairs['c12_aj'] = pairs['c12_aj'].map(type_c12_dict)
        pairs['func'] = 1
        # Intermolecular interactions learned from PDB are excluded 
        pairs['c6'].loc[(pairs['same_chain']=='No')] = 0.
        # If we don't have any other chain the next c12 loc throws an error, so I made this check
        check = pairs.loc[pairs['same_chain']=='No']
        if not check.empty:
            pairs['c12'].loc[(pairs['same_chain']=='No')] = np.sqrt(pairs['c12_ai'] * pairs['c12_aj'])  
        pairs.drop(columns = ['rc_probability','same_chain', 'c12_ai', 'c12_aj', 'check', 'exclude', 'epsilon', 'source'], inplace = True)
        pairs = pairs[['ai', 'aj', 'func', 'c6', 'c12']]
    else:
        pairs = pd.DataFrame()
    
    # Drop NaNs. This is an issue when adding the ligand ensemble.
    pairs.dropna(inplace=True)

    # Adding the c12 (I do it now because later is sbatti)
    atnum_type_top['c12'] = atnum_type_top['sb_type'].map(type_c12_dict)

    # Here we make a dictionary of the backbone oxygen as atom number
    backbone_nitrogen = atnum_type_top.loc[atnum_type_top['atom'] == 'N']
    backbone_carbonyl = atnum_type_top.loc[atnum_type_top['atom'] == 'C']
    backbone_oxygen = atnum_type_top.loc[atnum_type_top['atom'] == 'O']
    sidechain_cb = atnum_type_top.loc[atnum_type_top['atom'] == 'CB']

# For each backbone oxygen take the CB of the same residue and save in a pairs tuple
    pairs_14_ai, pairs_14_aj, pairs_14_c6, pairs_14_c12 = [], [], [], []
    for index, line_backbone_oxygen in backbone_oxygen.iterrows():
        line_sidechain_cb = sidechain_cb.loc[sidechain_cb['residue_number'] == (line_backbone_oxygen['residue_number'])].squeeze(axis=None)
        if not line_sidechain_cb.empty:
            pairs_14_ai.append(line_backbone_oxygen['atom_number'])
            pairs_14_aj.append(line_sidechain_cb['atom_number'])
            pairs_14_c6.append(0.0)
            pairs_14_c12.append(0.275*np.sqrt(line_backbone_oxygen['c12']*line_sidechain_cb['c12']))
            #pairs_14_c12.append(2.598570e-06)

    pairs_14 = pd.DataFrame(columns=['ai', 'aj', 'func', 'c6', 'c12'])
    pairs_14['ai'] = pairs_14_ai
    pairs_14['aj'] = pairs_14_aj
    pairs_14['func'] = 1
    pairs_14['c6'] = pairs_14_c6
    pairs_14['c12'] = pairs_14_c12

    pairs = pd.concat([pairs,pairs_14], axis=0, sort=False, ignore_index=True)


    # For each backbone carbonyl take the CB of the following residue and save in a pairs tuple
    pairs_14_ai, pairs_14_aj, pairs_14_c6, pairs_14_c12 = [], [], [], []
    for index, line_backbone_carbonyl in backbone_carbonyl.iterrows():
        line_sidechain_cb = sidechain_cb.loc[sidechain_cb['residue_number'] == (line_backbone_carbonyl['residue_number']+1)].squeeze(axis=None)
        if not line_sidechain_cb.empty:
            pairs_14_ai.append(line_backbone_carbonyl['atom_number'])
            pairs_14_aj.append(line_sidechain_cb['atom_number'])
            pairs_14_c6.append(0.0)

            pairs_14_c12.append(0.275*np.sqrt(line_backbone_carbonyl['c12']*line_sidechain_cb['c12']))
            #pairs_14_c12.append(2.598570e-06)

    pairs_14 = pd.DataFrame(columns=['ai', 'aj', 'func', 'c6', 'c12'])
    pairs_14['ai'] = pairs_14_ai
    pairs_14['aj'] = pairs_14_aj
    pairs_14['func'] = 1
    pairs_14['c6'] = pairs_14_c6
    pairs_14['c12'] = pairs_14_c12

    pairs = pd.concat([pairs,pairs_14], axis=0, sort=False, ignore_index=True)

    # For each backbone nitrogen take the CB of the previuos residue and save in a pairs tuple
    pairs_14_ai, pairs_14_aj, pairs_14_c6, pairs_14_c12 = [], [], [], []
    for index, line_backbone_nitrogen in backbone_nitrogen.iterrows():
        line_sidechain_cb = sidechain_cb.loc[sidechain_cb['residue_number'] == (line_backbone_nitrogen['residue_number']-1)].squeeze(axis=None)
        if not line_sidechain_cb.empty:
            pairs_14_ai.append(line_backbone_nitrogen['atom_number'])
            pairs_14_aj.append(line_sidechain_cb['atom_number'])
            pairs_14_c6.append(0.0)
            
            pairs_14_c12.append(0.35*np.sqrt(line_backbone_nitrogen['c12']*line_sidechain_cb['c12']))
            #pairs_14_c12.append(1.522581e-06)

    pairs_14 = pd.DataFrame(columns=['ai', 'aj', 'func', 'c6', 'c12'])
    pairs_14['ai'] = pairs_14_ai
    pairs_14['aj'] = pairs_14_aj
    pairs_14['func'] = 1
    pairs_14['c6'] = pairs_14_c6
    pairs_14['c12'] = pairs_14_c12

    pairs = pd.concat([pairs,pairs_14], axis=0, sort=False, ignore_index=True)

    inv_LJ = pairs[['aj', 'ai', 'func', 'c6', 'c12']].copy()
    inv_LJ.columns = ['ai', 'aj', 'func', 'c6', 'c12']
    pairs = pd.concat([pairs, inv_LJ], axis=0, sort = False, ignore_index = True)
    # Cleaning the duplicates (the left alpha pairs win on pairs that may be previously defined)
    pairs.sort_values(by = ['ai', 'aj', 'c6', 'c12'], ascending = [True, True, True, True], inplace = True)
    pairs = pairs.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    # drop inverse duplicates
    cols = ['ai', 'aj']
    pairs[cols] = np.sort(pairs[cols].values, axis=1)
    pairs = pairs.drop_duplicates(subset = ['ai', 'aj'], keep = 'first')
    pairs['ai'] = pairs['ai'].astype(int)
    pairs['aj'] = pairs['aj'].astype(int)

    # Here we want to sort so that ai is smaller than aj
    inv_pairs = pairs[['aj', 'ai', 'func', 'c6', 'c12']].copy()
    inv_pairs.columns = ['ai', 'aj', 'func', 'c6', 'c12']
    pairs = pd.concat([pairs,inv_pairs], axis=0, sort = False, ignore_index = True)
    pairs = pairs[pairs['ai']<pairs['aj']]
    
    pairs.sort_values(by = ['ai', 'aj'], inplace = True)

    pairs = pairs.rename(columns = {'ai': '; ai'})
    pairs['c6'] = pairs["c6"].map(lambda x:'{:.6e}'.format(x))
    pairs['c12'] = pairs["c12"].map(lambda x:'{:.6e}'.format(x))
    exclusion = pairs[['; ai', 'aj']].copy()

    return pairs, exclusion


def rename_chains():
    pass