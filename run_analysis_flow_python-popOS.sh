#!/bin/bash

# Seedmap wrapper works with MATLAB R2019a for some reason
# module purge
# module load python3 matlab/R2019a workbench/1.4.2

# MATLAB Runtime
# damien_utilities=/home/faird/shared/code/external/utilities
# MRE=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/

MRE=/usr/local/MATLAB/MATLAB_Runtime/v96/

# Example session files
ex_sub=sub-NDARINV003RTV85/ses-baselineYear1Arm1
dtseries=func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii
lmidthick=anat/sub-NDARINV003RTV85_ses-baselineYear1Arm1_hemi-L_space-MNI_mesh-fsLR32k_midthickness.surf.gii
rmidthick=anat/sub-NDARINV003RTV85_ses-baselineYear1Arm1_hemi-R_space-MNI_mesh-fsLR32k_midthickness.surf.gii
motion=func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat

# Directory must exist to be mounted
mkdir -p container_output/

START=$(date '+%s')

python3 ili_manager.py  --cwd $(pwd)            \
	analysis                                \
        --roi_dir       container_rois/         \
        --n_samples     10                      \
        --matlab        "$(which matlab)"       \
        --MRE           ${MRE}                  \
        --json_config   config.json             \
        --label         test_fd                 \
        ${ex_sub}/{${dtseries},${motion}}

END=$(date '+%s')

minutes=$(( (END - START) / 60 ))
echo "Elapsed time: ${minutes} minutes"