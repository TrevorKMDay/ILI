import argparse
import subprocess as sp
import os
import pprint

pp = pprint.PrettyPrinter(indent=2)

###############################################################################

parser = argparse.ArgumentParser(description='Process some integers.')

parser.add_argument("input_dir", type=str,
                    help="Session dir to run seedmap on.")

parser.add_argument("output_dir", type=str,
                    help="Top-level directory to save sub/ses output")

parser.add_argument("-R", "--roi_files", nargs=2, metavar=("LH", "RH"),
                    required=True,
                    help="Left/right files containing ROIs")

parser.add_argument("-l", "--l_rois", type=str, nargs="*", metavar="l",
                    help="List of LH ROI indices.")

parser.add_argument("-r", "--r_rois", type=str, nargs="*",  metavar="r",
                    help="List of RH ROI indices.")

parser.add_argument("-f", "--fd", default=0.2,
                    help="FD threshold, default: 0.2")

parser.add_argument("-o", "--remove_outliers", action="store_true",
                    help="Remove motion outliers.")

parser.add_argument("-m", "--min_minutes", metavar="MINUTES",
                    help="Number of minutes from scan to use, default: all")

parser.add_argument("-z", "--Z_transform", action="store_true",
                    help="Create Z-transformation of map")

parser.add_argument("-p", "--dtseries_pattern",
                    default="sub-*_ses-*_task-rest_bold_desc-" +
                            "filtered_timeseries.dtseries.nii",
                    help="File glob to help find dtseries in input dir")

args = parser.parse_args()

assert args.l_rois is not None or args.r_rois is not None, \
    "Must supply at least one ROI"

# print(args)

###############################################################################

bash_script = "/home/feczk001/day00096/laterality/code/bash/run-seedmap.sh"

###############################################################################

input_dir = os.path.abspath(args.input_dir)
output_dir = os.path.abspath(args.output_dir)
os.makedirs(output_dir, exist_ok=True)

pp.pprint([input_dir, output_dir])

# Each of these need to be constructed as lists of args to be appended later
l_rois_flag = ["-l", " ".join(args.l_rois)] if args.l_rois is not None else []
r_rois_flag = ["-r", " ".join(args.r_rois)] if args.r_rois is not None else []
minutes_flag = ["-m", args.min_minutes] if args.min_minutes is not None else []
z_flag = ["-z"] if args.Z_transform is not None else []

# Flag with no arguments
rm_out_flag = "-x" if args.remove_outliers is not None else ""

# Search pattern to find dtseries in input directory, may need to be added as
# an option later.
dtseries_pattern = args.dtseries_pattern

cmd = [bash_script,
       "-d", dtseries_pattern,
       "-f", args.fd,
       "-i", input_dir, "-o", output_dir,
       "-L", args.roi_files[0], "-R", args.roi_files[1],
       rm_out_flag] + \
       minutes_flag + \
       l_rois_flag + r_rois_flag + \
       z_flag

cmd_str = [str(x) for x in cmd]

pp.pprint(cmd_str)

sp.run(cmd_str)
