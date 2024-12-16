import argparse
# import re
# import random
import subprocess as sp
import shutil
# import glob
import sys
# import os
import json

import numpy as np
# import pandas as pd
import pprint
# import tempfile as tf

from ili_analysis import analyze_session
from ili_ili import calculate_ILI
from ili_rois import create_rois

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

ps_roi = subparsers.add_parser("roi",
                               help="1. Create ROIs")

ps_analysis = subparsers.add_parser("analysis",
                                    help="2. Analyze session")
ps_ili = subparsers.add_parser("ili",
                               help="3. Calculate ILI from analysis CSV files")

ps_fd = subparsers.add_parser("fd",
                              help="Extract FD values from .mat file.")

ps_config = subparsers.add_parser("config",
                                  help="Create basic config file.")

ps_version = subparsers.add_parser("version",
                                   help="Get the current version")

VERSION = "v0.8.0"

# ROI CREATION OPTIONS ====

# Input ROI
ps_roi.add_argument("-i", "--input_roi", dest="input_roi",
                    help="CIFTI file containing LEFT hemisphere ROI to work "
                         "with. Does not currently support R->L.",
                    metavar="FILE",
                    required=True)

# How many variations at each L/R greyordinate ratio to create
ps_roi.add_argument("-n", "--n_repeats", dest="n",
                    default=10,
                    type=int,
                    help="How many alternative versions at each mixing "
                         "ratio L/R to create. Default: 10.",
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

# Other flags

# TO DO: Make this a positional argument
ps_analysis.add_argument("-r", "--roi_dir", dest="roi_dir",
                         default="/input_rois/",
                         help="Directory containing label files to use",
                         metavar="DIR")

# TO DO: Make this a positional argument
ps_analysis.add_argument("-c", "--json_config", dest="config_file",
                         default="/config.json",
                         help="JSON file containing configuration for "
                              "seedmapper",
                         metavar="FILE")

ps_analysis.add_argument("-l", "--label", dest="label",
                         default="crossotope",
                         help="Prefix for output CSV",
                         metavar="STR")

ps_analysis.add_argument("-n", "--n_samples", dest="n",
                         default=100,
                         type=int,
                         help="How many mixing values to use.",
                         metavar="N")

ps_analysis.add_argument("-m", "--MRE", dest="mre_dir",
                         default="/matlab",
                         help="MATLAB runtime directory; R2019a recommended",
                         metavar="DIR")

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

ps_fd.add_argument("--stat", "-s",
                   choices=["TR", "frames", "sec", "FD"],
                   help="Which stat to extract: TR, frames remaining, "
                        "seconds remaining, FD remaining")

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

# RUN

# Check for wb command existence (only roi or analysis)

if args.command == "roi" or args.command == "analysis":

    wb_command = shutil.which("wb_command")

    if wb_command is None:
        sys.exit("ERROR: wb_command not found with `which`")
    else:
        print(f"wb_command path is:\n\t{wb_command}")


def extract_fd(mat_file, fd, stat=None):

    cmd = ["Rscript", f"{args.cwd}/bin/fd-fd_extraction.R", mat_file, fd]

    if stat is not None:
        cmd += [stat]

    fd_results = sp.run(cmd,
                        check=False,
                        stdout=sp.PIPE, stderr=sp.DEVNULL,
                        universal_newlines=True)

    # pp.pprint(fd_results)

    warning_string = "WARNING: ignoring environment value of R_HOME"
    fd_results_str = fd_results.stdout.rstrip().replace(warning_string, '')
    fd_results = float(fd_results_str)

    # print(f"{mat_file}, FD < {fd}mm")
    return fd_results


# MAIN EXECUTION ===

if args.command == "version":

    print(f"Version: {VERSION}")

elif args.command == "roi":

    create_rois(input_roi=args.input_roi, n=args.n, prefix=args.roi_prefix,
                wb_command=wb_command)

elif args.command == "analysis":

    if args.midthickness is None:
        l_midthick_file = None
        r_midthick_file = None
    else:
        l_midthick_file = args.midthickness[0]
        r_midthick_file = args.midthickness[1]

    results = analyze_session(dtseries_file=args.dtseries_file,
                              motion_file=args.motion_file,
                              roi_dir=args.roi_dir, n=n_samples,
                              config=config,
                              matlab=args.matlab, mre_dir=args.mre_dir,
                              label=args.label,
                              l_midthick_file=l_midthick_file,
                              r_midthick_file=r_midthick_file,
                              halfway=args.halfway_only)

    pp.pprint(results)

    if args.cwd != "/home":
        results_f = f"{args.cwd}/{args.label}_results.csv"
    else:
        results_f = f"/output/{args.label}_results.csv"

    np.savetxt(results_f, results, delimiter=",",
               fmt="%s", header="nrh,ix,L,R", comments="")

elif args.command == "ili":

    calculate_ILI(directory=args.ili_directory, output_file=args.ili_output,
                  sizes=sizes)

elif args.command == "fd":

    fd = extract_fd(args.mat_file, args.FD, args.stat)

    print(f"Requested stat '{args.stat}' is: {fd}")

elif args.command == "config":

    config = {"fd_threshold": 0.2, "smoothing_kernel": 0, "max_minutes": 5,
              "remove_outliers_yn": 1, "z_transform_yn": 1,
              "cluster_surf_area_min": 10, "cluster_value_min": 0.4}

    with open(args.out, "w") as f:
        json.dump(config, f, indent=4)
