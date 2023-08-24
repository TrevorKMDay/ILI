# ILI

Trevor Day // day00096@umn.edu

Code to create the Singularity container for ILI ROI creation and processing.

## Setup

This repository relies on a second repository as a submodule. When cloning for
the first time, run the following code (see this [StackOverflow answer][1]).

    git submodule update --recursive --remote

## Running ROI creation

The container requires two bind points: the input ROI and the location to save
the created crossotopes to.

The directory containing the ROI gets bound to `/roi` and the outputs to
`/roi_outputs`. The name of the file must still be passed to the container
with `--input_roi`. The output directory does not.

    roi_name=example.dscalar.nii
    roi_outputs=container_rois

    # This is done to make sure too many ROIs aren't created
    rm -rf ${roi_outputs}
    mkdir -p ${roi_outputs}

    singularity run                         \
        -B data/example_roi/:/roi           \
        -B ${roi_outputs}:/roi_outputs      \
        my_img.sif roi                      \
            --input_roi /roi/${roi_name}    \
            -n 10

The ROI creation:

 1. Creates a mirror of your input on the right hemisphere. (Needs update to
        start in the right hemisphere.)
 1. Generates `n` different `dscalars` for each value of `nrh` between 1 and
        the total size of your ROI. So if you ask for `-n 10` repeats of a
        100-greyordinate ROI,  you will create 100 ROIs.
 2. The `dscalars` are mapped onto `dlabel` files (in `fsLR32k` space: needs
        update to add `164k` space).
 3. The `dlabel`s are split into left/right `label.gii` files. Only the GIFTIs
        are saved from all this processing: You don't need any of the other
        files.

### ROI tree

    ili_manager.py
        |- rois_create_mirror.sh
        |- rois_permute_ROI.R
        |- rois_dscalar_to_surface.sh

## Running analysis

The analysis works best using _derivatives_ from the DCAN Labs
[ABCD pipelines][2].

The analysis flow requires a lot more bind points. From top to bottom:

 1. The directory containing the `dtseries`, `.mat` file and optionally,
        `midthickness` files (L/R).
 2. The directory containing the ROIs created using the ROI flow above.
 3. The Matlab runtime directory. `R2019a` is known to work with this code.
 4. The JSON configuration file for the analysis parameters (see below).
 5. The directory to save the output CSV to. One CSV per session.

The options to the container itself are more self-explanatory.

 - The positional arguments are:
    - `dtseries_file`: The path to the dtseries file .
    - `motion_file`: The path to the motion `.mat` file.
 - Required flagged arguments`*`
    - `--roi_dir` takes the path to the ROIs and figures out how many there
        are.
    - The path to the Matlab binary (`--matlab`), since I can't package it in
        the container.
    - The path to the Matlab runtime (`--MRE`).
    - The path to the JSON config file, which should be bound to the container
        (`--json_config`.)
 - Other flagged arguments:
    - `--n_samples` is how many ROIs to use (e.g. if the ROI is 500
        greyordinates, you don't have to use them all). The default value is
        100.
    - Finally, the `--label` is prepended to the results, e.g.
       `foobar_results.csv`. Default: "crossotope"

### Config file

All options regarding the processing itself (e.g. motion limits, minute limits)
are included in a configuration JSON file, see below. This also makes the
CLI options less overwhelming to navigate.

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

Default values are those listed in example above. NB: You can't include
comments in actual JSON files.

### Example usage:

    MRE=${path_to_MRE}/MATLAB_Runtime_R2019a_update9/v96/

    singularity run \
        -B ${ex_sub}/:/session/            \
        -B container_rois/:/input_rois/    \
        -B ${MRE}:/matlab/                 \
        -B config.json:/config.json        \
        -B container_output:/output/       \
        my_img.sif analysis                \
            --roi_dir       /input_rois        \
            --n_samples     100                \
            --matlab        "$(which matlab)"  \
            --MRE           /matlab            \
            --json_config   /config.json       \
            --label         foobar             \
            /session/{${dtseries},${motion}}

See [brace expansion][3] if the `/session/{1,2}` context is unfamiliar.

#### Minutes

`dtseries` files with less than 10 minutes of good data will be run; the output
files have a different name than those that met the criterion.

Files with less than 30 s of good data will not be run at all.

#### Z-threshold

Currently, the no-transformation option isn't complete. Keep it set to 1.

### Analysis tree

    ili_manager.py
        |- analysis-run_seedmap.sh
            |- seedmap_wrapper.py
                |- Cifti_conn_matrix_to_corr_dt_pt
                |- MATLAB
        |- analysis-cluster.sh

## Benchmarks

On [MSI](https://www.msi.umn.edu/)

 - **ROI creation**:
       With 16 GB RAM: 7-8 minutes for 490 total ROIs (1 s/ROI,
       or 61 ROIs/minute).
 - **Analysis:**
       With 56 GB RAM: 20 minutes for 100 samples (12 s/ROI or 5 samples per
       minute).

[1]: https://stackoverflow.com/questions/1030169/pull-latest-changes-for-all-git-submodules

[2]: https://github.com/DCAN-Labs/abcd-hcp-pipeline

[3]: https://www.gnu.org/software/bash/manual/html_node/Brace-Expansion.html