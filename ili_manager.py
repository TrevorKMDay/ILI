import argparse
import re
import random

import subprocess as sp
import shutil
import glob
import sys
import os
import json

import numpy as np

# Newlines in help
from argparse import RawTextHelpFormatter

# import sys; print(sys.version)
# exit()

# PARSE OPTIONS

parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help',
                    formatter_class=RawTextHelpFormatter)

parser.add_argument("-F", "--flow", dest="flow",
                    nargs="?", choices=("roi", "analysis"),
                    required=True,
                    help="Use ROI creation  ('roi') or analysis flow "
                         "('analysis')",
                    metavar="FLOW")

## ROI CREATION OPTIONS ====

# Input ROI
parser.add_argument("-i", "--roi_input", dest="roi_input",
                    help="CIFTI file containing ROI to create.",
                    metavar="FILE")

# How many variations at each L/R greyordinate ratio to create
parser.add_argument("-n", "--n_repeats", dest="n", 
                    type=int, 
                    help="1. When ROI flow: How many alternative versions at "
                         "each mixing ratio L/R to create.\n"
                         "2. When analysis flow: How many mixing values to "
                         "use.",
                    metavar="N")

## ANALYSIS OPTIONS ====

# Session input
parser.add_argument("-s", "--session", dest="session_files", nargs=4,
                    help="Files to analyze: dtseries, L/R midthickness, motion",
                    metavar="FILE")

parser.add_argument("-r", "--roi_dir", dest="roi_dir",
                    help="Directory containing label files to use",
                    metavar="DIR")

parser.add_argument("-j", "--json_config", dest="config_file",
                    help="JSON file containing configuration for seedmapper",
                    metavar="FILE")

parser.add_argument("-m", "--MRE", dest="mre_dir",
                    help="MATLAB runtime directory; R2019a recommended",
                    metavar="DIR")


args = parser.parse_args()

# Declare functions

def create_rois(roi_input, n):

    print("\n=== Running ROI flow ... ===")

    # Check input
    if roi_input is not None:
        if ".dscalar.nii" in roi_input:
            # Copy input file to standard name
            sp.run(["cp", roi_input, "original_roi.dscalar.nii"])
            roi_input = "original_roi.dscalar.nii"
        else:
            sys.exit(f"ERROR: Input ROI {roi_input} should be a .dscalar.nii "
                      "file")
    else:
        # ROI needs to be supplied for ROI-making flow
        sys.exit("ERROR: Input ROI required")

    ## 1. Create mirror file
    print("\n== Creating mirrored ROI ==")
    roi_mirrored="flipped_roi.dscalar.nii"
    sp.run(["bin/rois_create_mirror.sh", wb_command, roi_input, roi_mirrored])

    ## 2. Create permutations
    print("\n== Creating permutations ==")
    output_dir="roi_outputs"
    os.makedirs(output_dir, exist_ok=True)
    sp.run(["Rscript", "bin/rois_permute_ROI.R", 
            wb_command, roi_input, roi_mirrored, str(n), output_dir, "test"])

    ## 3. Convert all dscalars -> dlabel.nii -> label.gii
    print("\n== Converting to label files ==")
    sp.run(["bin/rois_dscalar_to_surface.sh", output_dir])

    ## 4. Clean up
    n_dscalar = len(glob.glob(f"{output_dir}/*.dscalar.nii"))
    n_dlabel = len(glob.glob(f"{output_dir}/*.dlabel.nii"))
    n_labelg = len(glob.glob(f"{output_dir}/*.label.gii"))

    # Check to make sure theres one dlabel per dscalar
    if not n_dscalar == n_dlabel:
        sys.exit(f"Error: Number of dscalars ({n_dscalar}) and dlabels "
                 f"({n_dlabel}) does not match!. Exiting.")

    # Check to make sure there's two .label.gii files per dlabel
    if not 2 * n_dlabel == n_labelg:
        sys.exit(f"Error: Number of 2 * dlabels ({n_dlabel}) and label files "
                 f"({n_labelg}) does not match! Exiting.")

    # Remove unnecessary files
    print("\n== Removing old dscalar/dlabels ==")
    [os.remove(i) for i in glob.glob(f"{output_dir}/*.dscalar.nii")]
    [os.remove(i) for i in glob.glob(f"{output_dir}/*.dlabel.nii")]

def analyze_session(session_files, roi_dir, n, config_file, mre_dir):

    print("\n=== Running analysis flow ... ===")

    ## Check for MATLAB existence
    matlab = shutil.which("matlab")

    if matlab is None:
        sys.exit("ERROR: matlab not found with `which`")
    else:
        print(f"matlab path is:\n\t{matlab}")

    # Check input files
    if session_files is not None:

        if ".dtseries.nii" in session_files[0]:
            # Simplify legibility of code
            dtseries = session_files[0]
            print(f"dtseries is:\n\t{session_files}")
        else:
            sys.exit("ERROR: Input session file 1 should be a .dtseries.nii "
                     "file")

        if ".surf.gii" in session_files[1]:
            # Simplify legibility of code
            l_midthick_file = session_files[1]
            print(f"L midthick is:\n\t{l_midthick_file}")
        else:
            sys.exit("ERROR: Input session file 2 should be a .surf.gii file")

        if ".surf.gii" in session_files[2]:
            # Simplify legibility of code
            r_midthick_file = session_files[2]
            print(f"R midthick is:\n\t{r_midthick_file}")
        else:
            sys.exit("ERROR: Input session file 3 should be a .surf.gii file")

        if ".mat" in session_files[3]:
            # Simplify legibility of code
            motion_file = session_files[3]
            print(f"Motion file is:\n\t{motion_file}")
        else:
            sys.exit("ERROR: Input session file 4 should be a .mat file")

    else:
        # Session needs to be supplied for session flow
        sys.exit("ERROR: Input session files required")

    # Load in ROIs
    if roi_dir is not None:
        
        rois = [f for f in os.listdir(roi_dir) if 
                os.path.isfile(os.path.join(roi_dir, f))]

        # Extract # of unique nrh values
        size = len(set([re.findall(r"nrh-[0-9]+", f)[0] for f in rois]))

        indices = len(set([re.findall(r"ix-[0-9]+", f)[0] for f in rois]))

        print(f"Found {size} ROIs with {indices} copies each.")

        # Select n ratios from those available
        sizes_to_use = random.sample(list(range(1, size)), n)
        sizes_to_use.sort()

        # For each size selected, choose an index to use for that ROI
        indices_to_use = [int(random.uniform(1, indices)) for i in sizes_to_use]
                          
        # TO DO: zfill assumes sizes of exactly 3 for size and 2 for index
        sizes_to_use_str = [str(i).zfill(3) for i in sizes_to_use]
        indices_to_use_str = [str(i).zfill(2) for i in indices_to_use]

        # Zip ratios, indices
        ROIs_to_use_str= zip(sizes_to_use_str, indices_to_use_str)
        # Structure (nrh, ix, [L, R])
        # Find these files in the original directory
        files_to_use = [glob.glob(f"{roi_dir}/*_nrh-{nrh}_ix-{ix}_?.label.gii") 
                        for nrh, ix in ROIs_to_use_str]

        # Store numeric values, file destination
        ROIs = zip(range(0, n), sizes_to_use, indices_to_use, 
                   files_to_use)

        # print([n, len(sizes_to_use), len(indices_to_use), len(files_to_use),
        #        len(list(ROIs))])
        # exit()

    else:
        # ROIs need to be supplied for session flow
        sys.exit("ERROR: Directory of ROIs required")

    if config_file is not None:

        config = json.load(open(config_file))
        print(config)

    else:
        # Config needs to be supplied for session flow
        sys.exit("ERROR: Config file needs to be supplied")

    # Create empty array with size n(x)4: NRH, IX, L, R
    results = np.zeros((n, 4), dtype=np.int64)

    for n, nrh, ix, files in ROIs:

        # TO DO: Don't hardcode this width
        nrh_zpad=str(nrh).zfill(3)

        # Params
        #   1: MRE; 2/3: L/R ROI; 
        #   4-7: session dtseries, l/r midthickness, motion
        #   8: FD; 9: smoothing kernel; 10: rm outliers?; 11: minutes; 
        #   12: Z-transformation?
        # Note: sp.run seems to require all args to be strings
        sp.run(["bin/analysis-run_seedmap.sh", 
                nrh_zpad,
                mre_dir,
                files[0], files[1], 
                dtseries, l_midthick_file, r_midthick_file, motion_file,  
                str(config['fd_threshold']),
                str(config['smoothing_kernel']), 
                str(config['remove_outliers_yn']),
                str(config['max_minutes']),
                str(config['z_transform_yn'])
                ])

        cluster = sp.run(["bin/analysis-cluster.sh", 
                          f"seedmap_dir_{nrh_zpad}",
                          str(config["cluster_value_min"]),
                          str(config["cluster_surf_area_min"])],
                          capture_output=True)

        # Log cluster info
        print(cluster.stdout.decode('ascii'))

        result1 = re.findall(r'RESULT: \[\d+ \d+\]', 
                            cluster.stdout.decode('ascii'))[0]
        result2 = result1.replace("RESULT: ", "")
        result3 = re.sub(r'[\[\]]', '', result2).split(' ')

        # Add results to array
        results[n, 0] = nrh
        results[n, 1] = ix
        results[n, 2] = int(result3[0])
        results[n, 3] = int(result3[1])

        # break

    return(results)

# RUN 

## Check for wb command existence
wb_command = shutil.which("wb_command")

if wb_command is None:
    sys.exit("ERROR: wb_command not found with `which`")
else:
    print(f"wb_command path is:\n\t{wb_command}")

if args.flow == "roi":

    create_rois(args.input_roi)

elif args.flow == "analysis":

    results = analyze_session(args.session_files, args.roi_dir, args.n,
                              args.config_file, args.mre_dir)

    np.savetxt("results.csv", results, delimiter=",", fmt="%s",
               header="nrh,ix,L,R")