#!/bin/bash

# Seedmap wrapper works with MATLAB R2019a for some reason
module purge
module load python3 matlab/R2019a workbench/1.5.0 gcc/9.2.0

damien_utilities=/home/faird/shared/code/external/utilities

# MATLAB Runtime
MRE=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/
# MRE=${damien_utilities}/MATLAB_Runtime_R2019a/
# MRE=${damien_utilities}/MATLAB_Runtime_2020a_Update_7_glnxa64/v98
# MRE=${damien_utilities}/MATLAB_Runtime_R2021a/v910/
MRE=$(pwd)/MATLAB_Runtime_R2019a_update9_v96/
MRE=/common/software/install/manual/matlab/R2023b/

# echo $MRE

# Example session files
ex_sub=sub-NDARINV003RTV85/ses-baselineYear1Arm1
dtseries=func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii
# lmidthick=anat/sub-NDARINV003RTV85_ses-baselineYear1Arm1_hemi-L_space-MNI_mesh-fsLR32k_midthickness.surf.gii
# rmidthick=anat/sub-NDARINV003RTV85_ses-baselineYear1Arm1_hemi-R_space-MNI_mesh-fsLR32k_midthickness.surf.gii
motion=func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat

# Directory must exist to be mounted
mkdir -p container_output/

START=$(date '+%s')

python3 ili_manager.py  --cwd "$(pwd)"     \
	analysis                           \
        --roi_dir       container_rois/    \
        --n_samples     10                 \
        --matlab        "$(which matlab)"  \
        --MRE           ${MRE}             \
        --json_config   config.json        \
        --label         test_matlab        \
        ${ex_sub}/{${dtseries},${motion}}

END=$(date '+%s')

minutes=$(( (END - START) / 60 ))
echo "Elapsed time: ${minutes} minutes"
