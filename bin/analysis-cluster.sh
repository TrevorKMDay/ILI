#!/bin/bash

set -e

echolog(){
    # file=${tempdir}/info.txt
    # touch ${file}
    echo -e "(${1} cluster): ${2}" # | tee -a "${file}"
}

input_dir=${1}
SURF_VAL_THRESH=${2}
SURF_AREA_THRESH=${3}

echo
echolog INFO "STARTING CLUSTER SCRIPT"
echolog INFO "Value threshold: ${SURF_VAL_THRESH}"
echolog INFO "SA threshold:    ${SURF_AREA_THRESH}"

# Surfaces for refernce
ex_surf=$(dirname "${0}")/../data/example_sub/sub-example_hemi

# Find input directory and extract sub label
file=$(find "${input_dir}/" -name "*_roi-1_Z.dscalar.nii")

if [ "${file}" == "" ] ; then
    echolog ERROR "Can't find Z transformed dscalar in ${input_dir}/"
    echolog ERROR "  Pattern: *_roi-1_Z.dscalar.nii"
    echolog ERROR "${file}"
    exit 11
else
    echolog INFO "Found file ${file}"
fi

suffix=v${SURF_VAL_THRESH}_sa${SURF_AREA_THRESH}

cluster_dir=${input_dir}/clustering
mkdir -p "${cluster_dir}"

# Use -cifti-find-clusters to threshold and find minimum area (then count in
#   the next step)
wb_command -cifti-find-clusters \
    "${file}"                                           \
    "${SURF_VAL_THRESH}" "${SURF_AREA_THRESH}"          \
    0 0                                                 \
    COLUMN                                              \
    "${cluster_dir}/clustered_${suffix}.dscalar.nii"    \
    -left-surface  "${ex_surf}-L_space-MNI_mesh-fsLR32k_midthickness.surf.gii" \
    -right-surface "${ex_surf}-R_space-MNI_mesh-fsLR32k_midthickness.surf.gii"

# Invert ROI and use as mask to remove vertices from ROI from data
wb_command -cifti-math \
    "x * (mask == 0)"                                           \
    "${cluster_dir}/clustered_${suffix}_masked.dscalar.nii"     \
    -var x    "${cluster_dir}/clustered_${suffix}.dscalar.nii"   \
    -var mask "${input_dir}/session.dlabel.nii"

wb_command -cifti-math \
    "x * (mask > 0)"                                \
    "${cluster_dir}/values_in_cluster.dscalar.nii"  \
    -var x      "${file}"                           \
    -var mask   "${cluster_dir}/clustered_${suffix}_masked.dscalar.nii"

# Separate in order to score counts

wb_command -cifti-separate \
    "${cluster_dir}/clustered_v${SURF_VAL_THRESH}_sa${SURF_AREA_THRESH}.dscalar.nii" \
    COLUMN                                                                  \
    -metric CORTEX_LEFT  "${cluster_dir}/cortex_left_${suffix}.func.gii"    \
    -metric CORTEX_RIGHT "${cluster_dir}/cortex_right_${suffix}.func.gii"

nL=$(wb_command -metric-stats "${cluster_dir}/cortex_left_${suffix}.func.gii" \
        -reduce COUNT_NONZERO)
nR=$(wb_command -metric-stats "${cluster_dir}/cortex_right_${suffix}.func.gii" \
        -reduce COUNT_NONZERO)

echolog INFO "RESULT: [${nL} ${nR}]"