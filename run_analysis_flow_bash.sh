#!/bin/bash

# Seedmap wrapper works with MATLAB R2019a for some reason
module purge
module load python3 matlab/R2019a

damien_utilities=/home/faird/shared/code/external/utilities

# MATLAB Runtime
MRE=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/

# wb_command
export PATH="${damien_utilities}/workbench/1.4.2/workbench/bin_rh_linux64/:${PATH}"
which wb_command

# Example session files
ex_sub=sub-NDARINV003RTV85/ses-baselineYear1Arm1
dtseries=${ex_sub}/func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii
lmidthick=${ex_sub}/anat/sub-NDARINV003RTV85_ses-baselineYear1Arm1_hemi-L_space-MNI_mesh-fsLR32k_midthickness.surf.gii
rmidthick=${ex_sub}/anat/sub-NDARINV003RTV85_ses-baselineYear1Arm1_hemi-R_space-MNI_mesh-fsLR32k_midthickness.surf.gii
motion=${ex_sub}/func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat

python3 --version

python3 ili_manager.py --cwd "$(pwd)" analysis          \
    -s ${dtseries} ${lmidthick} ${rmidthick} ${motion}  \
    -r container_rois                                   \
    -n 100                                              \
    -m ${MRE}                                           \
    -M "$(which matlab)"                                \
    -j config.json