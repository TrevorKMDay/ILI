#!/bin/bash

# Assign variables

mre=${1}
L_ROI=${2}
R_ROI=${3}
input_dtseries=${4}
input_Lmidthickness=${5}
input_Rmidthickness=${6}
input_motion_mat=${7}
FD=${8}
SK=${9}
rm_OUTLIER=${10}
minutes=${11}
z_transform=${12}

# Exported with wrapper
seed_map_wrapper=Cifti_conn_matrix_to_corr_dt_pt/seed_map_wrapper.py

# Export cache root: This probably doesn't need to be done in a container, but
# I know it works

MCR_CACHE_ROOT=$(mktemp -d /tmp/mcr.XXXXXX)
export MCR_CACHE_ROOT

# Run seedmap

tempdir=seedmap_dir
# Create output directory and exit if unsuccessful
mkdir -p "${tempdir}" || (echo "Unable to create tempdir ${tempdir}" && exit 1)

echolog(){
    file=${tempdir}/info.txt
    # touch ${file}
    echo -e "${1}" | tee -a "${file}"
}

echo    "----------------"
echolog "Input:"
echolog "\t${input_dtseries}"
echolog "\t${input_Lmidthickness}"
echolog "\t${input_Rmidthickness}"
echolog "ROIs:"
echolog "\tL: ${L_ROI}"
echolog "\tR: ${R_ROI}"
echolog "Output directory:\t${tempdir}"
echolog "MCR cache:\t\t${MCR_CACHE_ROOT}"
echolog "RH ROI file:\t\t${R_ROI}"
echolog "LH ROI file:\t\t${L_ROI}"
echolog "FD threshold:\t\t${FD}"
echolog "Smoothing kernel:\t${SK}"
echolog "Outlier removal:\t${rm_OUTLIER}"
echolog "Minimum data minutes:\t${minutes}"
echolog "Z-transform:\t\t${z_transform}"
echo    "----------------"
echo

for i in ${L_ROI} ${R_ROI} ; do
    if [ ! -e "${i}" ] ; then
        echo "ERROR: ROI file \"${i}\" doesn't exist, exiting."
        exit 1
    fi
done

# Check dtseries exists
if [ -e "${input_dtseries}" ] ; then
    TR=$(wb_command -file-information -only-step-interval "${input_dtseries}")
    echo -e "Found TR: ${TR} s\n"
else
    echo "MISSING dtseries: ${input_dtseries}"
    exit 1
fi

################################################################################
# Create custom ptseries

labelfile=${tempdir}/session.dlabel.nii
ptseriesfile=${tempdir}/session.ptseries.nii

# Apply labels
wb_command -cifti-create-dense-from-template \
    "${input_dtseries}" \
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

echo    "Done with:"
echo -e "\t${labelfile}"
echo -e "\t${ptseriesfile}"

################################################################################
# Create conc files

dtseries_conc=${tempdir}/dtseries.conc
ptseries_conc=${tempdir}/ptseries.conc
lmt_conc=${tempdir}/lmidthick.conc
rmt_conc=${tempdir}/rmidthick.conc
motion_conc=${tempdir}/motion.conc

# Input file .conc files
readlink -f "${input_dtseries}" > "${dtseries_conc}"
readlink -f "${ptseriesfile}"   > "${ptseries_conc}"
readlink -f "${input_Lmidthickness}" > "${lmt_conc}"
readlink -f "${input_Rmidthickness}" > "${rmt_conc}"

# Copy motion.mat to seedmap directory (it works better this way)
local_mat_file="${tempdir}/motion.mat"
cp "${input_motion_mat}" "${local_mat_file}"
readlink -f "${local_mat_file}" > "${motion_conc}"

################################################################################
# Run

echo
echo "Seed mapping"
echo "------------"
wb_command=$(which wb_command)
echo -e "WB:\t${wb_command}"
echo -e "MRE:\t${mre}"
echo "Seed map wrapper: ${seed_map_wrapper}"
echo

output=${tempdir}/seedmaps
mkdir -p "${output}"

for i in ${lmt_conc} ${rmt_conc} ${dtseries_conc} ${ptseries_conc} ; do
    if [ ! -e "${i}" ] ; then
        echo "Important file (${i}) doesn't exist"
        exit 1
    fi
done

# For flags where 0 means don't do, add that here:

if [ "${SK}" == 0 ] ; then 
    SK_FLAG=""
else
    SK_FLAG="--smoothing_kernel ${SK}"
fi

if [ "${rm_OUTLIER}" == 0 ] ; then
    OUTLIER_FLAG=""
else
    OUTLIER_FLAG="--remove-outliers"
fi

if [ "${minutes}" == 0 ] ; then
    MIN_FLAG=""
else
    MIN_FLAG="--minutes ${minutes}"
fi

run_and_z () {

    # The last argument to 'cmd' is 1, each input ROI file must have only one
    #   ROI (labeled 1).

    cmd="
        python3 ${seed_map_wrapper}       \
            --mre-dir       ${mre}         \
            --wb_command    ${wb_command}  \
            --source        Cifti_conn_matrix_to_corr_dt_pt/ \
            --fd-threshold  ${FD}          \
            --left          ${lmt_conc}    \
            --right         ${rmt_conc}    \
            --motion        ${motion_conc} \
            --output        ${output}      \
            ${SK_FLAG}                    \
            ${OUTLIER_FLAG}               \
            ${MIN_FLAG}                   \
            ${TR}                         \
            ${dtseries_conc}              \
            ${ptseries_conc}              \
            1
        "

    # Echo cmd to log and then run
    echo "${cmd}" | tr -s "[:blank:]" " "
    ${cmd}

    # Check to see if a file was created with the appropriate name
    file_created=$(find "${tempdir}" -name "*task-rest_*_ROI1.dscalar.nii")

    if [ "${file_created}" == "" ] ; then
        echo "Output from seedmap not created, exiting"
        exit 1
    fi

    new_file="${file_created//_ROI/_roi-}"
    mv "${file_created}" "${new_file}"
    echo "Created:  ${new_file}"
    echo

    if [ "${z_transform}" == 1 ] ; then

        z_dscalar="${new_file%.dscalar.nii}_Z.dscalar.nii"

        if [ ! -e "${z_dscalar}" ] ; then

            # equation from Z14
            wb_command -cifti-math                           \
                '(0.5*ln((1+r)/(1-r)))'                      \
                "${z_dscalar}" \
                -var r "${new_file}"

            echo

        fi

        echo "Created ${z_dscalar}"

    fi

}

run_and_z 
