import os
import sys
import glob
import subprocess as sp


def create_rois(input_roi, n, prefix, wb_command):

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
