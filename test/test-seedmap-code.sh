#!/bin/bash

# Seedmap wrapper works with MATLAB R2019a for some reason
module purge
module load python3 matlab/R2019a workbench/1.4.2

# MATLAB Runtime
damien_utilities=/home/faird/shared/code/external/utilities
MRE=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/


# Files
ses=sub-NDARINV003RTV85/ses-baselineYear1Arm1/
dtseries=${ses}/func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii

# Setup ptseries ===============================================================

ROI_L=container_rois/foobar2_nrh-001_ix-01_L.label.gii
ROI_R=container_rois/foobar2_nrh-001_ix-01_R.label.gii

# Apply labels
wb_command -cifti-create-dense-from-template \
    "${dtseries}" \
    "${labelfile}"      \
    -label              \
        CORTEX_LEFT     \
        "${L_ROI}"      \
    -label              \
        CORTEX_RIGHT    \
        "${R_ROI}"

# Create ptseries
wb_command -cifti-parcellate    \
    "${input_dtseries}"         \
    "${labelfile}"              \
    COLUMN                      \
    "${ptseriesfile}"           \
    -method MEAN                \
    -legacy-mode

# Parameters
TR=0.8
FD=0.2

python Cifti_conn_matrix_to_corr_dt_pt/seed_map_wrapper.py \
    -fd  ${FD}  \
    -mre ${MRE} \
    ${TR} ${dtseries}