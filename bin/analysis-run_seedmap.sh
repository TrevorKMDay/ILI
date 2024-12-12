#!/bin/bash

# Assign variables

# readlink resolves symlinks for the user

nrh=${1}
matlab=${2}
mre=${3}
L_ROI=$(readlink -f "${4}")
R_ROI=$(readlink -f "${5}")
input_dtseries=$(readlink -f "${6}")
input_Lmidthickness=$(readlink -f "${7}")
input_Rmidthickness=$(readlink -f "${8}")
if [ "${9}" != "NONE" ] ; then
    input_motion_mat=$(readlink -f "${9}")
else
    input_motion_mat=NONE
fi
FD=${10}
SK=${11}
rm_OUTLIER=${12}
minutes=${13}
z_transform=${14}
tempdir=${15}


# The seedmap wrapper is consistently located in this place relative to this
#   file.
seed_map_wrapper=$(dirname "${0}")/../Cifti_conn_matrix_to_corr_dt_pt/seed_map_wrapper.py

# Export cache root: This probably doesn't need to be done in a container, but
# I know it works
matlab_dir=$(dirname "${matlab}")
MCR_CACHE_ROOT=$(mktemp -d /tmp/mcr.XXXXXX)

export PATH=${matlab_dir}:${PATH}
export MCR_CACHE_ROOT

# Run seedmap

echolog(){
    file=${tempdir}/info.txt
    # touch ${file}
    echo -e "(${1} run_seedmap): ${2}" | tee -a "${file}"
}

echo
echolog INFO "Input:"
echolog INFO "\t${input_dtseries}"
echolog INFO "\t${input_Lmidthickness}"
echolog INFO "\t${input_Rmidthickness}"
echolog INFO "\t${input_motion_mat}"
echolog INFO "ROIs:"
echolog INFO "\tL: ${L_ROI}"
echolog INFO "\tR: ${R_ROI}"
echolog INFO "Output directory:\t${tempdir}"
echolog INFO "MCR cache:\t\t${MCR_CACHE_ROOT}"
echolog INFO "RH ROI file:\t\t${R_ROI}"
echolog INFO "LH ROI file:\t\t${L_ROI}"
echolog INFO "FD threshold:\t\t${FD}"
echolog INFO "Smoothing kernel:\t${SK}"
echolog INFO "Outlier removal:\t${rm_OUTLIER}"
echolog INFO "Minimum data minutes:\t${minutes}"
echolog INFO "Z-transform:\t\t${z_transform}"
echo

if [[ "${L_ROI}" == "" ]] ; then
    echolog ERROR "L ROI file is missing, exiting!"
    exit 1
fi

for i in ${L_ROI} ${R_ROI} ; do
    if [ ! -e "${i}" ] ; then
        echolog ERROR "ROI file \"${i}\" doesn't exist, exiting."
        exit 1
    fi
done

# Check dtseries exists
if [ -e "${input_dtseries}" ] ; then
    TR=$(wb_command -file-information -only-step-interval "${input_dtseries}")
    echolog INFO "Found TR: ${TR} s\n"
else
    echolog ERROR "MISSING dtseries: ${input_dtseries}"
    exit 1
fi

################################################################################
# Create custom ptseries

labelfile=${tempdir}/session.dlabel.nii
ptseriesfile=${tempdir}/session.ptseries.nii

# Apply labels
wb_command -cifti-create-dense-from-template \
    "${input_dtseries}"             \
    "${labelfile}"                  \
    -label CORTEX_LEFT  "${L_ROI}"  \
    -label CORTEX_RIGHT "${R_ROI}"

# Create ptseries
wb_command -cifti-parcellate    \
    "${input_dtseries}"         \
    "${labelfile}"              \
    COLUMN                      \
    "${ptseriesfile}"           \
    -method MEAN                \
    -legacy-mode

echolog INFO "Done with: ${labelfile}"
echolog INFO "Done with: ${ptseriesfile}"

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
# echo -e "\t${input_motion_mat}"
if [ "${input_motion_mat}" != "NONE" ] ; then
    local_mat_file="${tempdir}/motion.mat"
    cp "${input_motion_mat}" "${local_mat_file}"
    readlink -f "${local_mat_file}" > "${motion_conc}"
    MOTION_FLAG="--motion ${motion_conc}"
else
    MOTION_FLAG=""
fi

# Check all files exist

for i in ${lmt_conc} ${rmt_conc} ${dtseries_conc} ${ptseries_conc} ; do
    if [ ! -e "${i}" ] ; then
        echolog ERROR "Important file (${i}) doesn't exist"
        exit 1
    fi
done

# RUN SEEDMAP ##################################################################

wb_command=$(which wb_command)

echo
echolog INFO "Seed mapping"
echolog INFO "WB:\t${wb_command}"
echolog INFO "MRE:\t${mre}"
echolog INFO "Seed map wrapper: ${seed_map_wrapper}"
echo

output=${tempdir}/seedmaps
mkdir -p "${output}"

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
        python3 ${seed_map_wrapper}                             \
            --mre-dir       ${mre}                              \
            --wb_command    ${wb_command}                       \
            --source        $(dirname "${seed_map_wrapper}")    \
            --fd-threshold  ${FD}                               \
            --left          ${lmt_conc}                         \
            --right         ${rmt_conc}                         \
            ${MOTION_FLAG}                                      \
            --output        ${output}                           \
            ${SK_FLAG}                                          \
            ${OUTLIER_FLAG}                                     \
            ${MIN_FLAG}                                         \
            ${TR}                                               \
            ${dtseries_conc}                                    \
            ${ptseries_conc}                                    \
            1
        "

    # Echo cmd to log and then run
    echo "${cmd}" | tr -s "[:blank:]" " "
    ${cmd}

    # Check to see if a file was created with the appropriate name
    #   Include "minutes" to check that

    echolog INFO "Looking for file ..."
    file_created=$(find "${tempdir}" \
                    \( -name "*minutes*_ROI1.dscalar.nii" -o \
                       -name "*_all_frames_at_FD_none_ROI1.dscalar.nii" \) )

    echolog INFO "Found: ${file_created}"

    if [ "${file_created}" == "" ] ; then
        echolog ERROR \
            "Output from seedmap not created, exiting, check ${tempdir}"
        exit 100
    fi

    # Rename output of MATLAB code to more closely align to BIDS naming
    #   standards
    new_file_bn="$(basename "${file_created}" | sed 's/_ROI/_roi-/')"
    new_file="${tempdir}/${new_file_bn}"
    mv "${file_created}" "${new_file}"
    echolog INFO "Created ${new_file}"
    echo

    if [ "${z_transform}" == 1 ] ; then

        z_dscalar="${new_file%.dscalar.nii}_Z.dscalar.nii"

        if [ ! -e "${z_dscalar}" ] ; then

            # equation from Z14
            wb_command -cifti-math      \
                '(0.5*ln((1+r)/(1-r)))' \
                "${z_dscalar}"          \
                -var r "${new_file}"

            echo

        fi

        echo INFO "Created ${z_dscalar}"

    fi

}

run_and_z
