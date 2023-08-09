#!/bin/bash

# Seedmap wrapper works with MATLAB R2019a for some reason
module purge
module load python3 matlab/R2019a workbench/1.4.2

projhome=/home/feczk001/day00096/ili_container

# MATLAB Runtime
damien_utilities=/home/faird/shared/code/external/utilities
MRE=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/

# Files
ses=${projhome}/sub-NDARINV003RTV85/ses-baselineYear1Arm1/
dtseries=${ses}/func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii

# Setup ptseries ===============================================================

L_ROI=${projhome}/container_rois/foobar2_nrh-001_ix-01_L.label.gii
R_ROI=${projhome}/container_rois/foobar2_nrh-001_ix-01_R.label.gii

if [ ! -e test.dlabel.nii ] ; then

    echo "Creating dlabel"

    # Apply labels
    wb_command -cifti-create-dense-from-template \
        "${dtseries}"       \
        test.dlabel.nii     \
        -label              \
            CORTEX_LEFT     \
            "${L_ROI}"      \
        -label              \
            CORTEX_RIGHT    \
            "${R_ROI}"

fi

if [ ! -e test.ptseries.nii ] ; then

    echo "Creating ptseries"

    # Create ptseries
    wb_command -cifti-parcellate    \
        "${dtseries}"               \
        test.dlabel.nii             \
        COLUMN                      \
        test.ptseries.nii           \
        -method MEAN                \
        -legacy-mode

fi

# Parameters
TR=0.8
FD=0.2
mat=${ses}/func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat

echo "Trying bare"

python ${projhome}/Cifti_conn_matrix_to_corr_dt_pt/seed_map_wrapper.py \
    -fd  ${FD}  \
    -mre ${MRE} \
    -m   ${mat} \
    ${TR} ${dtseries} test.ptseries.nii 1


echo -e "\n============"
echo      "Trying concs"
echo -e   "============\n"

echo ${dtseries} > d.conc
echo test.ptseries.nii > p.conc

python ${projhome}/Cifti_conn_matrix_to_corr_dt_pt/seed_map_wrapper.py \
    -fd  ${FD}  \
    -mre ${MRE} \
    -m   ${mat} \
    ${TR} {d,p}.conc 1