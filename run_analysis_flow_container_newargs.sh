#!/bin/bash

# Seedmap wrapper works with MATLAB R2019a for some reason
module purge
module load python3 matlab/R2019a

damien_utilities=/home/faird/shared/code/external/utilities

# MATLAB Runtime
MRE=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/

# Example session files
ex_sub=sub-NDARINV003RTV85/ses-baselineYear1Arm1
dtseries=func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii
motion=func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat

# ls -lrh ${ex_sub}/{${dtseries},${motion}} ; exit

# Directory must exist to be mounted
mkdir -p container_output/

START=$(date '+%s')

singularity run \
    -B ${ex_sub}/:/session/                 \
    -B container_rois/:/input_rois/         \
    -B ${MRE}:/matlab/                      \
    -B config.json:/config.json             \
    -B container_output:/output/            \
    -B ili_manager.py:/home/ili_manager.py  \
    crossotope.sif analysis                 \
        --roi_dir       /input_rois         \
        --n_samples     10                   \
        --matlab        "$(which matlab)"   \
        --MRE           /matlab             \
        --json_config   /config.json        \
        --label         test_newargs        \
        /session/{${dtseries},${motion}}

END=$(date '+%s')

minutes=$(( (END - START) / 60 ))
echo "Elapsed time: ${minutes} minutes"

# python3 ili_manager.py analysis                  \
#     -s ${dtseries} ${lmidthick} ${rmidthick} ${motion}  \
#     -r roi_outputs                                      \
#     -n 100                                              \
#     -m ${MRE}                                           \
#     -j config.json