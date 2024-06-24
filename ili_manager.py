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
import pandas as pd
import pprint
import tempfile as tf

# Newlines in help
from argparse import RawTextHelpFormatter

# import sys; print(sys.version)
# exit()

pp = pprint.PrettyPrinter(indent=4)

# PARSE OPTIONS =====

parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog="Run roi --help or analysis --help for more "
                           "details",
                    formatter_class=RawTextHelpFormatter)

subparsers = parser.add_subparsers(dest="command")

ps_roi = subparsers.add_parser("roi", help="1. Create ROIs")
ps_analysis = subparsers.add_parser("analysis", help="2. Analyze session")
ps_ili = subparsers.add_parser("ili",
                               help="3. Calculate ILI from analysis CSV files")
ps_fd = subparsers.add_parser("fd", help="Extract FD values from .mat file.")
ps_config = subparsers.add_parser("config", help="Create basic config file.")
ps_version = subparsers.add_parser("version", help="Get the current version")

VERSION = "v0.5.1-rocky8"

# ROI CREATION OPTIONS ====

# Input ROI
ps_roi.add_argument("-i", "--input_roi", dest="input_roi",
                    help="CIFTI file containing LEFT hemisphere ROI to work "
                         "with. Does not currently support R->L.",
                    metavar="FILE",
                    required=True)

# How many variations at each L/R greyordinate ratio to create
ps_roi.add_argument("-n", "--n_repeats", dest="n",
                    type=int, default=10,
                    help="How many alternative versions at each mixing "
                         "ratio L/R to create.",
                    metavar="N")

ps_roi.add_argument("-p", "--prefix", dest="roi_prefix",
                    default="crossotope",
                    help="Prefix to output: PFX_nrh-X_ix-Y.dlabel.nii",
                    metavar="STR")

# ANALYSIS OPTIONS ====

# Session input

# New version
ps_analysis.add_argument(dest="dtseries_file",
                         help="dtseries file")

ps_analysis.add_argument(dest="motion_file",
                         help="Motion file (ends in .mat)")

ps_analysis.add_argument("--midthickness", nargs=2,
                         metavar="FILE",
                         help="Midthickness files for smoothing: L, R")

# ps_analysis.add_argument("-L", "--left_midthickness",
#                          dest="left_midthick_file",
#                          help="Left midthickness file",
#                          metavar="FILE")

# ps_analysis.add_argument("-R", "--right_midthickness",
#                          dest="right_midthick_file",
#                          help="Right midthickness file",
#                          metavar="FILE")

# Other flags

ps_analysis.add_argument("-r", "--roi_dir", dest="roi_dir",
                         help="Directory containing label files to use",
                         metavar="DIR", default="/input_rois/")

# TO DO: Make this a positional argument
ps_analysis.add_argument("-c", "--json_config", dest="config_file",
                         help="JSON file containing configuration for "
                              "seedmapper",
                         metavar="FILE", default="/config.json")

ps_analysis.add_argument("-l", "--label", dest="label",
                         help="Prefix for output CSV",
                         default="crossotope",
                         metavar="STR")

ps_analysis.add_argument("-n", "--n_samples", dest="n",
                         type=int, default=100,
                         help="How many mixing values to use.",
                         metavar="N")

ps_analysis.add_argument("-m", "--MRE", dest="mre_dir",
                         help="MATLAB runtime directory; R2019a recommended",
                         metavar="DIR",
                         required=True)

ps_analysis.add_argument("-M", "--matlab", dest="matlab",
                         help="Path to MATLAB binary.",
                         metavar="FILE",
                         required=True)

ps_analysis.add_argument("--halfway_only", dest="halfway_only",
                         action="store_true")

# ILI options =======

ps_ili.add_argument(dest="ili_directory",
                    help="Directory of CSV files.")

ps_ili.add_argument(dest="ili_output",
                    help="CSV file to save ILI values to.")

ps_ili.add_argument("-s", "--sizes_file", dest="sizes_file",
                    help="JSON containing max ROI sizes",
                    metavar="JSON")

# FD options ======

ps_fd.add_argument(dest="mat_file",
                   help=".mat motion file to extract params from")

ps_fd.add_argument(dest="FD",
                   default=0.2,
                   help="FD thresh to use: 0.0 to 0.5 in steps of 0.01")

# Config options

ps_config.add_argument(dest="out",
                       help=".json file to save to")

# SHARED OPTIONS

parser.add_argument("--cwd", dest="cwd",
                    help="Current working directory",
                    default="/home",
                    metavar="DIR")

args = parser.parse_args()

# print(args)

# If no subcommand given, give help.
if not args.command:
    parser.parse_args(["--help"])
    sys.exit(0)

# print(args)
# sys.exit()

# Check arguments

if args.command == "analysis":

    if args.config_file is not None:

        print("Configuration:")
        config = json.load(open(args.config_file))
        pp.pprint(config)
        print(type(config))
        print()

    else:
        # Config needs to be supplied for analysis flow
        sys.exit("ERROR: Configuration file needs to be supplied")

    if config["smoothing_kernel"] == 0:
        print(" INFO: Smoothing kernel is 0, doing no smoothing.\n")
    else:
        print(f" INFO: Smoothing kernel is {config['smoothing_kernel']}.\n")

        if args.midthickness is None:
            print("   ERROR: --midthickness must be supplied if smoothing"
                  " kernel is >0.")
            sys.exit(1)

    if args.halfway_only:
        n_samples = 1
    else:
        n_samples = args.n

if args.command == "ili":

    if args.sizes_file is None:
        print("WARNING: Supplying a sizes_file is highly recommended!\n")
        sizes = None
    else:
        sizes = json.load(open(args.sizes_file))
        print(f"INFO: Found a file with sizes for {len(sizes)} ROIs\n")
        # pp.pprint(sizes)


# Declare functions

def write_csv(df, csv_file):

    # Write to CSV without index column and then remove '#' from header row
    df.to_csv(csv_file, index=False)

    print(f"{csv_file} saved!")


def create_rois(input_roi, n, prefix):

    print("\n=== Running ROI flow ... ===")

    output_dir = "/roi_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Check input
    if input_roi is not None:
        if ".dscalar.nii" in input_roi:
            # Copy input file to standard name
            sp.run(["cp", input_roi, f"{output_dir}/original_roi.dscalar.nii"])
            input_roi = f"{output_dir}/original_roi.dscalar.nii"
        else:
            sys.exit(f"ERROR: Input ROI {input_roi} should be a .dscalar.nii "
                     "file")
    else:
        # ROI needs to be supplied for ROI-making flow
        sys.exit("ERROR: Input ROI required")

    # 1. Create mirror file
    print("\n== Creating mirrored ROI ==")
    roi_mirrored = f"{output_dir}/flipped_roi.dscalar.nii"
    sp.run(["bin/rois_create_mirror.sh", wb_command, input_roi, roi_mirrored])

    # 2. Create permutations
    print(f"\n== Creating permutations ({n})==")
    sp.run(["Rscript", "bin/rois_permute_ROI.R",
            wb_command, input_roi, roi_mirrored, str(n), output_dir, prefix])

    # 3. Convert all dscalars -> dlabel.nii -> label.gii
    print("\n== Converting to label files ==")
    sp.run(["bin/rois_dscalar_to_surface.sh", wb_command, output_dir])

    # 4. Clean up
    n_dscalar = len(glob.glob(f"{output_dir}/{prefix}_*.dscalar.nii"))
    n_dlabel = len(glob.glob(f"{output_dir}/{prefix}_*.dlabel.nii"))
    n_labelg = len(glob.glob(f"{output_dir}/{prefix}_*.label.gii"))

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


def analyze_session(dtseries_file, motion_file,
                    roi_dir, n, config, matlab, mre_dir,
                    l_midthick_file=None, r_midthick_file=None,
                    halfway=False):

    """
    Given a session, create the table of LI per seed laterality

    :param str dtseries_file: The path to the dtseries file (ends in
                                dtseries.nii).
    :param str motion_file: The path to the motion file (ends in .mat)
    :param str roi_dir: The path to the directory containing the crossotopes
                        (created with roi subcommand)
    :param int n: The number of subsamples to take
    :param list config: The config file read in to python.
    :param str matlab: The path to the MATLAB executable.
    :param str mre_dir: The path to the MATLAB Runtime directory.
    :param str l_midthick_file: The path to the left midthickness file (only if
                                smoothing.)
    :param str r_midthick_file: As above.

    """

    print("\n=== Running analysis flow ... ===")

    # TO DO: Check matlab is properly executable

    # Check input files
    # os.path.realpath resolves relative paths, symlinks the user gives it

    if ".dtseries.nii" in dtseries_file:
        # Simplify legibility of code
        dtseries = os.path.realpath(dtseries_file)
        print(f"dtseries is:\n\t{dtseries_file}")
    else:
        sys.exit("ERROR: First input should be a .dtseries.nii file")

    if ".mat" in motion_file:

        # Simplify legibility of code
        motion_file = os.path.realpath(motion_file)
        print(f"Motion file is:\n\t{motion_file}")

        # sp.run(["Rscript", "{args.cwd}/bin/fd_extraction.R", motion_file,
        #         config["fd_threshold"]],
        #        stdout="/output/data_info.txt")

        # exit()

    elif motion_file == "NONE":
        motion_file = "NONE"
        print(f"Motion file is:\n\t{motion_file}")
    else:
        sys.exit("ERROR: Second input should be a .mat file or NONE")

    # Check midthickness files if given
    if l_midthick_file is not None and ".surf.gii" in l_midthick_file:
        # Simplify legibility of code
        l_midthick_file = os.path.realpath(l_midthick_file)
        print(f"L midthick is:\n\t{l_midthick_file}")
    elif l_midthick_file is not None and ".surf.gii" not in l_midthick_file:
        sys.exit("ERROR: Input session file 2 should be a .surf.gii file")

    if r_midthick_file is not None and ".surf.gii" in r_midthick_file:
        # Simplify legibility of code
        r_midthick_file = os.path.realpath(r_midthick_file)
        print(f"L midthick is:\n\t{r_midthick_file}")
    elif r_midthick_file is not None and ".surf.gii" not in r_midthick_file:
        sys.exit("ERROR: Input session file 2 should be a .surf.gii file")

    # Load in ROIs
    if roi_dir is not None:

        rois = [f for f in os.listdir(roi_dir) if
                os.path.isfile(os.path.join(roi_dir, f))]

        # print(rois)
        # print([re.findall(r"nrh-[0-9]+", f)[0] for f in rois
        #         if ".label.gii" in f])

        roi_labels = [f for f in rois if ".label.gii" in f]

        # Extract # of unique nrh values
        size = len(set([re.findall(r"nrh-[0-9]+", f)[0] for f in roi_labels]))

        if size < n:
            print(f"Requested # of samples ({n}) is smaller than size, "
                  f"({size}), setting n to {size}.")
            n = size

        indices = len(set([re.findall(r"ix-[0-9]+", f)[0] for f in
                           roi_labels]))

        # Find the first index to get the width for zero-padding
        index1 = [re.findall(r"ix-[0-9]+", f)[0] for f in roi_labels][0]
        # Returns "ix-\d+", don't count "ix-"
        ix_zpad = len(index1) - 3

        print(f"Found {size} ROIs with {indices} copies each.")

        if not halfway:

            # Select n ratios from those available
            sizes_to_use = random.sample(list(range(1, size + 1)), n)
            sizes_to_use.sort()

        else:
            sizes_to_use = list(range(round(size / 2), round(size / 2) + 1))

        print(f"Using sizes {sizes_to_use}")

        # For each size selected, choose an index to use for that ROI
        indices_to_use = [int(random.uniform(1, indices)) for i in
                          sizes_to_use]

        # TO DO: zfill assumes sizes of exactly 3 for size and 2 for index
        sizes_to_use_str = [str(i).zfill(3) for i in sizes_to_use]
        indices_to_use_str = [str(i).zfill(ix_zpad) for i in indices_to_use]

        # Zip ratios, indices
        ROIs_to_use_str = zip(sizes_to_use_str, indices_to_use_str)
        # Structure (nrh, ix, [L, R])
        # Find these files in the original directory
        files_to_use = [glob.glob(f"{roi_dir}/*_nrh-{nrh}_ix-{ix}_?.label.gii")
                        for nrh, ix in ROIs_to_use_str]

        # Store numeric values, file destination
        ROIs = zip(range(0, n), sizes_to_use, indices_to_use, files_to_use)

        # print([n, len(sizes_to_use), len(indices_to_use), len(files_to_use),
        #        len(list(ROIs))])
        # exit()

    else:
        # ROIs need to be supplied for session flow
        sys.exit("ERROR: Directory of ROIs required")

    # Create empty array with size n(x)4: NRH, IX, L, R
    results = np.zeros((n, 4), dtype=np.int64)

    for n, nrh, ix, files in ROIs:

        if "_L.label.gii" in files[0]:
            l_roi_file = os.path.realpath(files[0])
            r_roi_file = os.path.realpath(files[1])
        elif "_L.label.gii" in files[1]:
            l_roi_file = os.path.realpath(files[1])
            r_roi_file = os.path.realpath(files[0])

        # TO DO: Don't hardcode this width
        nrh_zpad = str(nrh).zfill(3)

        # Matlab function ciftiopen() seems to want to run "-cifti-convert
        #   -to-gifti-ext" writing the output to the working directory (/home).
        # This doesn't work in a container, so chdir to the filesystem /tmp
        os.chdir("/tmp/")

        label = args.label

        # tf.TemporaryDirectory() creates the dir, but returns an object
        # - cast to name to pass to bash scripts
        with tf.TemporaryDirectory(prefix=f"{label}-{nrh_zpad}-") as \
                temp_dir_name:

            # temp_dir_name = temp_dir.name

            print(f"Working directory is: {temp_dir_name}")

            # Params
            #   1: Zero-padded NRH
            #   2-3: Where to find Matlab
            #   4-5: L/R ROI files
            #   6-9: session dtseries, l/r midthickness, motion
            #   10: FD; 11: smoothing kernel; 12: rm outliers?; 13: minutes;
            #   12: Z-transformation?
            # Note: sp.run seems to require all args to be strings
            p = sp.run([f"{args.cwd}/bin/analysis-run_seedmap.sh",
                        nrh_zpad,
                        matlab, mre_dir,
                        l_roi_file, r_roi_file,
                        dtseries,
                        str(l_midthick_file), str(r_midthick_file),
                        motion_file,
                        str(config['fd_threshold']),
                        str(config['smoothing_kernel']),
                        str(config['remove_outliers_yn']),
                        str(config['max_minutes']),
                        str(config['z_transform_yn']),
                        temp_dir_name],
                       check=False)

            seedmap_rc = p.returncode
            if seedmap_rc == 100:
                print("\nERROR: Insufficient minutes at"
                      f"<{config['fd_threshold']} FD in this dtseries.\n")
                sys.exit(100)

            print("Copying temp dir to home")
            sp.run(["ls", temp_dir_name])

            # setting check=True causes python to exit if this command fails
            # useful for dev, but not prod
            cluster = sp.run([f"{args.cwd}/bin/analysis-cluster.sh",
                              temp_dir_name,
                              str(config["cluster_value_min"]),
                              str(config["cluster_surf_area_min"])],
                             check=False,
                             stdout=sp.PIPE, stderr=sp.STDOUT,
                             universal_newlines=True)

            # Log cluster info
            print(cluster.stdout)

        result1 = re.findall(r'RESULT: \[\d+ \d+\]', cluster.stdout)[0]
        result2 = result1.replace("RESULT: ", "")
        result3 = re.sub(r'[\[\]]', '', result2).split(' ')

        # Add results to array
        results[n, 0] = nrh
        results[n, 1] = ix
        results[n, 2] = int(result3[0])
        results[n, 3] = int(result3[1])

        # print([nrh, ix, result3])

        # break

    return results


def calculate_ILI(directory, output_file):

    # Find all files in directory
    files = [f for f in os.listdir(directory)
             if os.path.isfile(os.path.join(directory, f))]

    # Reduce to CSV files
    csv_files = [os.path.join(directory, f) for f in files if ".csv" in f]

    print(f"Found {len(csv_files)} CSV files")

    results = []

    for csv in csv_files:

        # Get size of ROI by identifying ROI from the filename and looking it
        #   up.
        # csv_basename = os.path.basename(csv).replace("_results.csv", "")

        # Find `roi-foo`` label in filename, if not, fall back to automatic
        #   detection.
        if "roi-" in csv:
            roi_label = re.search(r'roi-[^_]*', csv)
            roi_name = roi_label.replace("roi-", "")

        else:
            print(f"Missing BIDS-like `roi-foo` in {csv}, cannot use this "
                  "to find size. Size will be set automatically.")

        if sizes is not None and roi_name in sizes.keys():
            size = sizes[roi_name]
            ILI = sp.run(["Rscript", "bin/ili-calculate_ILI.R", csv,
                          str(size)],
                         stdout=sp.PIPE)
        else:
            # If roi_name not found in json file, fall back
            print(f"Size for roi {roi_name} was not found, falling back to "
                  "automatic detection.")
            ILI = sp.run(["Rscript", "bin/ili-calculate_ILI.R", csv],
                         stdout=sp.PIPE)

        # Clean up file name
        shortname = str.replace(os.path.basename(csv), ".csv", "")

        # Build up dataframe
        results.append([shortname, float(ILI.stdout)])

    df = pd.DataFrame(results)
    df.columns = ["file", "ILI"]

    # My custom CSV wrapper
    write_csv(df, output_file)

# RUN

# Check for wb command existence (only roi or analysis)


if args.command == "roi" or args.command == "analysis":

    wb_command = shutil.which("wb_command")

    if wb_command is None:
        sys.exit("ERROR: wb_command not found with `which`")
    else:
        print(f"wb_command path is:\n\t{wb_command}")


def extract_fd(mat_file, fd):

    fd_results = sp.run(["Rscript", f"{args.cwd}/bin/fd_extraction.R",
                         mat_file, fd],
                        check=True,
                        stdout=sp.PIPE, stderr=sp.DEVNULL,
                        universal_newlines=True)

    fd_results_str = fd_results.stdout.rstrip()

    print(f"{mat_file}, {fd}, {fd_results_str}")

# MAIN EXECUTION ===


if args.command == "version":

    print(f"Version: {VERSION}")

elif args.command == "roi":

    create_rois(args.input_roi, args.n, args.roi_prefix)

elif args.command == "analysis":

    if args.midthickness is None:
        l_midthick_file = None
        r_midthick_file = None
    else:
        l_midthick_file = args.midthickness[0]
        r_midthick_file = args.midthickness[1]

    results = analyze_session(args.dtseries_file, args.motion_file,
                              args.roi_dir, n_samples,
                              config, args.matlab, args.mre_dir,
                              l_midthick_file=l_midthick_file,
                              r_midthick_file=r_midthick_file,
                              halfway=args.halfway_only)

    print(results)

    np.savetxt(f"/output/{args.label}_results.csv", results, delimiter=",",
               fmt="%s", header="nrh,ix,L,R", comments="")

elif args.command == "ili":

    calculate_ILI(args.ili_directory, args.ili_output)

elif args.command == "fd":

    extract_fd(args.mat_file, args.FD)

elif args.command == "config":

    config = {"fd_threshold": 0.2, "smoothing_kernel": 0, "max_minutes": 5,
              "remove_outliers_yn": 1, "z_transform_yn": 1,
              "cluster_surf_area_min": 10, "cluster_value_min": 0.4}

    with open(args.out, "w") as f:
        json.dump(config, f, indent=4)
