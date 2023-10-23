# Multi-*e*GO: a multi-ensemble Gō model
Original version by [Emanuele Scalone](https://github.com/emalacs), Cristina Paissoni, and [Carlo Camilloni](https://github.com/carlocamilloni), Computational Structural Biology Lab, Department of Biosciences, University of Milano, Italy.

**Codename: VANESSA (Beta 1)**

    Current Developers: Fran Bacic Toplek, Carlo Camilloni, Riccardo Capelli, Emanuele Scalone, Bruno Stegani

## Installation
Use conda and the enviroment file provided. 

## Requirements
Multi-*e*GO force-fields and tools are meant to be used with [GROMACS](https://www.gromacs.org), currently tested version are 2021 to 2023.

## Prepare your first multi-*e*GO system
The first step to perform a multi-*e*GO simulation is to generate a GROMACS topology file (.top). 
In a folder copy your PDB file and the multi-ego-basic.ff/ included here, then run 
> gmx pdb2gmx -f file.pdb -ignh

and select the multi-ego-basic force-field. From this you should get a (.gro) file for your structure and a (.top) topology file.
In the multi-eGO/input folder add a folder for your system and a reference/ subfolder. Copy your GROMACS topology in this reference/ subfolder 

## Setup of a multi-*e*GO random coil simulation

## Analysis of a reference simulation

## Setup of a multi-*e*GO production simulation 
    
## References
1. Scalone, E., et al. [Multi-eGO: An in silico lens to look into protein aggregation kinetics at atomic resolution.](https://www.pnas.org/doi/10.1073/pnas.2203181119) Proc Natl Acad Sci USA 119, e2203181119 (2022) preprint available: [bioRxiv](https://www.biorxiv.org/content/10.1101/2022.02.18.481033v2)
2. Bacic Toplek, F., Scalone, E., et al. [Multi-eGO: model improvements towards the study of complex self-assembly processes.]() preprint available: [bioRxiv]()

