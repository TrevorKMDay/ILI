import argparse
import shutil
import subprocess as sp
import os

# import sys; print(sys.version)
# exit()

# PARSE OPTIONS

parser = argparse.ArgumentParser(
                    prog = 'ProgramName',
                    description = 'What the program does',
                    epilog = 'Text at the bottom of help')

parser.add_argument("-F", "--flow", dest="flow",
                    nargs="?", choices=("roi", "analysis"),
                    required=True,
                    help="Use ROI creation flow or analysis flow",
                    metavar="FLOW")

# Input ROI
parser.add_argument("-i", "--roi_input", dest="roi_input",
                    help="CIFTI file containing ROI to create.",
                    metavar="FILE")

# How many variations at each L/R greyordinate ratio to create
parser.add_argument("-n", "--n_repeats", dest="n_repeats", 
                    type=int, default=10,
                    help="How many versions at each mixing % to create.",
                    metavar="N")

args = parser.parse_args()

# RUN 

## Check for wb command existence
wb_command = shutil.which("wb_command")

if wb_command is None:
    print("ERROR: wb_command not found with `which`")
    exit(1)
else:
    print("fwb_command path is {wb_command}")

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

    ## Create mirror file
    print("\n== Creating mirrored ROI ==")
    roi_mirrored="flipped_roi.dscalar.nii"
    sp.run(["bin/create_mirror.sh", wb_command, roi_input, roi_mirrored])

    # Create permutations
    print("\n== Creating permutations ==")
    output_dir="roi_outputs"
    os.makedirs(output_dir, exist_ok=True)
    sp.run(["Rscript", "bin/permute_ROI.R", 
            wb_command, roi_input, roi_mirrored, str(args.n_repeats),
            output_dir, "test"])