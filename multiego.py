import os
import pandas as pd
import sys, getopt
from read_input import read_pdbs, plainMD_mdmat, random_coil_mdmat#, read_topology_atoms, read_topology_bonds
from write_output import write_LJ, write_atomtypes_atp, write_topology, write_ligand_topology
from greta import make_pairs_exclusion_topology, PDB_LJ_pairs, MD_LJ_pairs, merge_and_clean_LJ, make_pdb_atomtypes, make_more_atomtypes, topology_check
from topology_parser import read_topology, topology_parser
from greta import ensemble, multiego_ensemble, sb_type_conversion#, add_ligand_atomic_mat
pd.options.mode.chained_assignment = None  # default='warn'

def main(argv):

    parameters = {
        # native pair distance cut-off, used only when learning from structures
        'distance_cutoff':5.5,
        # neighbor aminoacid to exclude < x, used only when learning from structures
        'distance_residue':2,
        # this is the minimum probability for a pair to be considered
        'md_threshold':0.0001,
        # this is the minimum probability for the random-coil matrix
        'rc_threshold':0.0000001,
        # Settings for LJ 1-4. We introduce some LJ interactions otherwise lost with the removal of explicit H
        # The c12 of a LJ 1-4 is too big, therefore we reduce by a factor
        'lj_reduction':0.25,
        # This is the interaction energy of the amyloid cross beta
        'epsilon_amyl':0.380,
        # Acid FFnonbondend it only works on the native pairs
        'acid_ff':False,
        # Default behavior is to train from a simulation
        'ensemble':True,
        # Does the model include the interaction with a ligand
        'ligand':False,
        # This is to reduce the kds when taking the ligand from another FF
        'ligand_reduction':6.75, # 2*1.5*1.5*1.5
        # The following parameters are added later from input arguments
        # TODO Add descriptions
        'protein':None,
        'egos':None,
        'epsilon_md':None,
        'input_folder':None,
        'output_folder':None
    }

    print('\n\nMulti-eGO (codename: GRETA)\n')

    readall=0

    try:
        opts, args = getopt.getopt(argv,"",["protein=","egos=","epsilon=", "ligand=", "noensemble","help"])
    except getopt.GetoptError:
        print('multiego.py --protein <protein> --egos <single|merge|rc> --epsilon=0.x (not used with --egos=rc) --noensemble (optional)')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '--help':
            print('multiego.py --protein <protein> --egos <single|merge|rc> --epsilon=0.x (not used with --egos=rc) --noensemble (optional)')
            sys.exit()
        elif opt in ("--protein"):
            if not arg:
                print('Provide a protein name')
                sys.exit()
            else:
                parameters['protein'] = arg
                readall +=1
        elif opt in ("--egos"):
            if arg in ('single', 'merge', 'rc'):
                parameters['egos'] = arg
                if arg == 'rc':
                    readall +=2
                else:
                    readall +=1
            else:
                print('--egos accepts <single|merge|rc> options')
                sys.exit()

        elif opt in ("--epsilon"):
            arg = float(arg)
            if arg > 1 or arg < 0:
                print('Epsilon values must be chosen between 0 and 1')
                sys.exit()
            else:
                parameters['epsilon_md'] = float(arg)
                readall +=1
        elif opt in ("--ligand"):
            arg = float(arg)
            if arg > 1 or arg < 0:
                print('Epsilon values must be chosen between 0 and 1')
            else:
                parameters['ligand'] = True
                parameters['epsilon_ligand'] = float(arg)
        
        elif opt in ("--noensemble"):
            parameters['ensemble'] = False 
  
    # TODO figure out valid parameter combinations
    # check if input parameter combination is valid

    parameters['input_folder'] = f"inputs/{parameters['protein']}"

    # Folders to save the output files generated by the script
    if parameters['egos'] == 'rc':
        parameters['output_folder'] = f"outputs/{parameters['protein']}_{parameters['egos']}"
    else:
        epsilon_string = f"e{parameters['epsilon_md']}"
        if parameters['ligand'] == True:
            parameters['output_folder'] = f"outputs/{parameters['protein']}_{parameters['egos']}_{epsilon_string}_ligand{parameters['epsilon_ligand']}"
        else:
            parameters['output_folder'] = f"outputs/{parameters['protein']}_{parameters['egos']}_{epsilon_string}"

    print('- Creating a multi-eGO force-field using the following parameters:')
    for k,v in parameters.items():
        if v == None: continue
        print('\t{:<20}: {:<20}'.format(k,v))
    
    try:
        os.mkdir(parameters['output_folder'])
    except OSError as error:
        pass

    multi_ego = multiego_ensemble(parameters)

    print('- Creating native ensemble')
    ego_native_parameters = {
        'topology_file':f"{parameters['input_folder']}/topol.top",
        'structure_file': f"{parameters['input_folder']}/native.pdb",
    }
    ego_native = ensemble(parameters=parameters, ensemble_parameters=ego_native_parameters)
    ego_native.prepare_ensemble()
    ego_native.get_parsed_topology()

    print('Adding native topology to multi-eGO ensemble')
    multi_ego.add_ensemble_top(ego_native)
    multi_ego.add_parsed_topology(ego_native)

    if parameters['egos'] != 'rc':
        print('- Adding Random Coil probability matrix to multi-eGO ensemble')
        # Multi-eGO always require the random coil probability
        ego_native.add_random_coil()
        multi_ego.add_structure_based_contacts(random_coil = ego_native.atomic_mat_random_coil)
    
        if parameters['ensemble'] == True:
            print('- Ensemble = True: creating MD ensemble')         
            ego_md_parameters = {
                'topology_file':f"{parameters['input_folder']}/topol_md.top",
                'structure_file': f"{parameters['input_folder']}/native_md.pdb",
                'mdmat_contacts_file': f"{parameters['input_folder']}/plainMD_contacts.ndx",
            }

            ego_md = ensemble(parameters = parameters, ensemble_parameters=ego_md_parameters)
            ego_md.prepare_ensemble()
            ego_md.add_MD_contacts()
            ego_md.convert_topology(ego_native)
            print(f'- The following contacts were converted: {ego_md.conversion_dict}')
            print('- Adding MD probability matrix to multi-eGO ensemble')
            multi_ego.add_structure_based_contacts(atomic_mat_plainMD = ego_md.atomic_mat_MD)
        
        else:
            print('- Adding Structure-Based contact pairs to multi-eGO ensemble')
            # TODO ci potrebbe piacere il fatto di avere SB e MD insieme della nativa?
            ego_native.get_structure_pairs()
            multi_ego.add_structure_based_contacts(native_pairs=ego_native.structure_pairs)

        if parameters['egos'] == 'merge':
            print('- Merge = True: creating fibril ensemble')
            ego_fibril_parameters = {
                'topology_file':f"{parameters['input_folder']}/fibril_temp/topol.top",
                'structure_file': f"{parameters['input_folder']}/fibril.pdb",
            }
            ego_fibril = ensemble(parameters = parameters, ensemble_parameters=ego_fibril_parameters)
            ego_fibril.prepare_ensemble()
            
            print('- Matching fibril topology to native topology')
            ego_fibril.match_native_topology(ego_native.sbtype_idx_dict)
            
            print('- Making fibril Structure-Based contact pairs')
            ego_fibril.get_structure_pairs(ego_native)
            
            print('- Adding fibril Structure-Based contact pairs to multi-eGO ensemble')
            multi_ego.add_structure_based_contacts(fibril_pairs = ego_fibril.structure_pairs)

        if parameters['ligand']:
            print('- Ligand = True: creating ligand ensemble')
            
            top = read_topology(f'{parameters["input_folder"]}/topol.top')
            ego_ligand_parameters = {
                'topology_file':f"{parameters['input_folder']}/topol_ligand.top",
                'structure_file': f"{parameters['input_folder']}/topol_native_ligand.pdb",
                'mdmat_contacts_file': f"{parameters['input_folder']}/ligandMD_contacts.ndx",
                'itp_file': f'{parameters["input_folder"]}/topol_ligand.itp',
                'prm_file': f'{parameters["input_folder"]}/topol_ligand.prm'
            }
            ego_ligand = ensemble(parameters=parameters, ensemble_parameters=ego_ligand_parameters)
            ego_ligand.prepare_ensemble()
            ego_ligand.add_MD_contacts()
            ego_ligand.convert_topology(ego_native)
            print(f'- The following contacts were converted: {ego_ligand.conversion_dict}')
            
            print('- Extracting ligand ensemble')
            ego_ligand.get_ligand_ensemble()
            ego_ligand.ligand_MD_LJ_pairs()
            
            #multi_ego.add_ensemble_top(ego_ligand)
            multi_ego.add_parsed_ligand_topology(ego_ligand)
            print('- Adding MD probability matrix to multi-eGO ensemble')
            multi_ego.add_structure_based_contacts(ligand_MD_pairs = ego_ligand.ligand_atomic_mat_MD)
        
    elif parameters['egos'] == 'rc':
        pass

    else: # one should never get here
        print("I dont' understand --egos=",parameters['egos'])
        exit()
    
    print('- Generating multi-eGO LJ')
    multi_ego.generate_multiego_LJ()
    
    print('- Generating pairs and exclusions for multi-eGO topology')
    multi_ego.generate_pairs_exclusions()
    print('- Generating writable')
    multi_ego.generate_outputs_toWrite()  

    print('- Writing multi-eGO Force-Field')
    write_atomtypes_atp(multi_ego)        
    write_LJ(multi_ego)
    write_topology(multi_ego)
    if parameters['ligand'] == True:
        write_ligand_topology(multi_ego)

    print('- Force-Field files saved in ' + parameters['output_folder'])
    print('\nGRETA completed! Carlo is happy!\t\^o^/\n')


if __name__ == "__main__":
   main(sys.argv[1:])
