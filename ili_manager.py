import argparse
import re
import random

import subprocess as sp
import shutil
import glob
import sys
import os
import json

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
parser.add_argument("-s", "--session", dest="session_file",
                    help="dtseries file to analyze",
                    metavar="FILE")

parser.add_argument("-r", "--roi_dir", dest="roi_dir",
                    help="Directory containing label files to use",
                    metavar="DIR")

parser.add_argument("-j", "--json_config", dest="config_file",
                    help="JSON file containing configuration for seedmapper",
                    metavar="FILE")


args = parser.parse_args()

# RUN 

## Check for wb command existence
wb_command = shutil.which("wb_command")

if wb_command is None:
    print("ERROR: wb_command not found with `which`")
    exit(1)
else:
    print(f"wb_command path is:\n\t{wb_command}")

if args.flow == "roi":

    print("\n=== Running ROI flow ... ===")

    # Check input
    if args.roi_input is not None:
        if ".dscalar.nii" in args.roi_input:
            # Simplify legibility of code
            sp.run(["cp", args.roi_input, "original_roi.dscalar.nii"])
            roi_input = "original_roi.dscalar.nii"
        else:
            print("ERROR: Input ROI should be a .dscalar.nii file")
            exit(1)
    else:
        # ROI needs to be supplied for ROI-making flow
        print("ERROR: Input ROI required")
        exit(1)

    ## 1. Create mirror file
    print("\n== Creating mirrored ROI ==")
    roi_mirrored="flipped_roi.dscalar.nii"
    sp.run(["bin/rois_create_mirror.sh", wb_command, roi_input, roi_mirrored])

    ## 2. Create permutations
    print("\n== Creating permutations ==")
    output_dir="roi_outputs"
    os.makedirs(output_dir, exist_ok=True)
    sp.run(["Rscript", "bin/rois_permute_ROI.R", 
            wb_command, roi_input, roi_mirrored, str(args.n),
            output_dir, "test"])

    ## 3. Convert all dscalars -> dlabel.nii -> label.gii
    print("\n== Converting to label files ==")
    sp.run(["bin/rois_dscalar_to_surface.sh", output_dir])

    ## 4. Clean up
    n_dscalar = len(glob.glob(f"{output_dir}/*.dscalar.nii"))
    n_dlabel = len(glob.glob(f"{output_dir}/*.dlabel.nii"))
    n_labelg = len(glob.glob(f"{output_dir}/*.label.gii"))

    if not n_dscalar == n_dlabel:
        sys.exit(f"Error: Number of dscalars ({n_dscalar}) and dlabels "
                 f"({n_dlabel}) does not match!. Exiting.")

    if not 2 * n_dlabel == n_labelg:
        sys.exit(f"Error: Number of 2 * dlabels ({n_dlabel}) and label files "
                 f"({n_labelg}) does not match! Exiting.")

    # Remove unnecessary files
    print("\n== Removing old dscalar/dlabels ==")
    [os.remove(i) for i in glob.glob(f"{output_dir}/*.dscalar.nii")]
    [os.remove(i) for i in glob.glob(f"{output_dir}/*.dlabel.nii")]

elif args.flow == "analysis":

    print("\n=== Running analysis flow ... ===")

    ## Check for MATLAB existence
    matlab = shutil.which("matlab")

    if matlab is None:
        print("ERROR: matlab not found with `which`")
        exit(1)
    else:
        print(f"matlab path is:\n\t{matlab}")

    if args.session_file is not None:
        if ".dtseries.nii" in args.session_file:
            # Simplify legibility of code
            session_file = args.session_file
            print(f"dtseries is:\n\t{session_file}")
        else:
            print("ERROR: Input ROI should be a .dtseries.nii file")
            exit(1)
    else:
        # Session needs to be supplied for session flow
        print("ERROR: Input session dtseries required")
        exit(1)

    # Load in ROIs
    if args.roi_dir is not None:
        
        rois = [f for f in os.listdir(args.roi_dir) if 
                os.path.isfile(os.path.join(args.roi_dir, f))]

        # Exctract # of unique nrh values
        size = len(set([re.findall(r"nrh-[0-9]+", f)[0] for f in rois]))

        indices = len(set([re.findall(r"ix-[0-9]+", f)[0] for f in rois]))

        print(f"Found {size} ROIs with {indices} copies each.")


        # Select n ratios from those available
        sizes_to_use = random.sample(list(range(1, size)), args.n)
        sizes_to_use.sort()

        # For each size selected, choose an index to use for that ROI
        indices_to_use = [int(random.uniform(1, indices)) for i in 
                          sizes_to_use]
                          
        # TO DO: zfill assumes sizes of exactly 3 for size and 2 for index
        sizes_to_use_str = [str(i).zfill(3) for i in sizes_to_use]
        indices_to_use_str = [str(i).zfill(2) for i in indices_to_use]

        # Zip ratios, indices
        ROIs_to_use_str= zip(sizes_to_use_str, indices_to_use_str)
        # Structure (nrh, ix, [L, R])
        # Find these files in the original directory
        files_to_use = [glob.glob(f"{args.roi_dir}/*_nrh-{nrh}_ix-{ix}_?.label.gii") 
                        for nrh, ix in ROIs_to_use_str]

        # Store numeric values, file destination
        ROIs = zip(sizes_to_use, indices_to_use, files_to_use)

        print(list(ROIs))

    else:
        # ROIs need to be supplied for session flow
        sys.exit("ERROR: Directory of ROIs required")

    if args.config_file is not None:

        config = json.load(open(args.config_file))
        print(config)

    else:
        # Config needs to be supplied for session flow
        sys.exit("ERROR: Config file needs to be supplied")