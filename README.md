# ILI

Trevor Day // day00096@umn.edu

Code to create the Singularity container for ILI ROI creation and processing.

# Running ROI creation

The container requires two bind points: the input ROI and the location to save
the created crossotopes to.

The directory containing the ROI gets bound to `/roi` and the outputs to
`/roi_outputs`. The name of the file must still be passed to the container
with `--input_roi`. The output directory does not.

    roi_name=example.dscalar.nii
    roi_dir=container_rois

    rm -rf ${roi_dir}
    mkdir -p ${roi_dir}

    singularity run                         \
        -B data/example_roi/:/roi           \
        -B ${roi_dir}:/roi_outputs          \
        my_img.sif roi                      \
            --input_roi /roi/${roi_name}    \
            -n 10

The ROI creation:

 1. Creates a mirror of your input on the right hemisphere. (Needs update to
        start in the right hemisphere.)
 1. Generates `n` different `dscalars` for each value of `nrh` between 0 and
        the total size of your ROI. So if you ask for `-n 10` repeats of a
        100-greyordinate ROI,  you will create 100 ROIs.
 2. The `dscalars` are mapped onto `dlabel` files (in `fsLR32k` space: needs
        update to add `164k` space).
 3. The `dlabel`s are split into left/right `label.gii` files. Only the GIFTIs
        are saved from all this processing: You don't need any of the other
        files.

# Running analysis

## Config file

To make it the command line options simpler to use, the options to the
seedmap wrapper are included in a configuration JSON file, e.g.

    {
        # Values for seedmap wrapper

        "fd_threshold":         0.2,    # Threshold in mm

        "smoothing_kernel":     0,      # Smoothing kernel in mm
                                        #   0 = none

        "max_minutes":          10,     # Minutes to sample from dtseries
                                        #   0 = no limit

        "remove_outliers_yn":   1,      # Whether to remove outliers (0/1)

        "z_transform_yn":       1       # Whether to Z-transform results (0/1)

        # Thresholds for determining laterality

        "cluster_value_min":        0.4     # Value to threshold map at

        "cluster_surf_area_min":    10,     # Minimum cluster size to keep
                                            #   (mm^2)
    }

Default values are those listed in example above. FYI no comments in actual
JSON files.

### Minutes

`dtseries` files with less than 10 minutes of good data will be run; the output
files have a different name than those that met the criterion.

Files with less than 30 s of good data will not be run at all.

### Z-threshold

Currently, the no-transformation option isn't complete. Keep it set to 1.

# Benchmarks

On [MSI](https://www.msi.umn.edu/)

 - **ROI creation**: With 16 GB RAM: 7-8 minutes for 490 total ROIs (1 s/ROI,
    or 61 ROIs/minute).
 - **Analysis:**
    with 56 GB RAM: 20 minutes for 100 samples (12 s/ROI
    or 5 samples per minute).
