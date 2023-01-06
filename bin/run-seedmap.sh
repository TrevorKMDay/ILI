#!/bin/bash
#set -e

#SBATCH --time=0:10:00
#SBATCH --ntasks=1
#SBATCH --mem=10g

# source=/home/feczk001/day00096/laterality/code/Cifti_conn_matrix_to_corr_dt_pt
projhome=/home/feczk001/day00096/laterality
source=${projhome}/code/seed_map_wrapper
seed_map_wrapper=${source}/seed_map_wrapper.py

cd ${projhome} || exit
# pwd

fez_utilities=/home/feczk001/shared/code/external/utilities
damien_utilities=/home/faird/shared/code/external/utilities

# Both put wb_cmd on PATH and save as a variable to pass to seed map wrapper
wb_dir=${fez_utilities}/workbench/1.4.2/workbench/bin_rh_linux64
wb_command=${wb_dir}/wb_command
export PATH=${wb_dir}:${PATH}

# Modules
module purge
# Use correct python, MATLAB 19a. Don't remember if parallel is used rn.
# Use Fez's wb instead of MSI, since MSI's is still glitchy
module load python/3.6.3 matlab/R2019a parallel
mre=${damien_utilities}/MATLAB_Runtime_R2019a_update9/v96/

MCR_CACHE_ROOT=$(mktemp -d /tmp/mcr.XXXXXX)
export MCR_CACHE_ROOT

################################################################################
# Find data

# We have been using 0.2, Z14 uses 0.5 with 1 pre and 2 post censoring.
# Power et al. (2014) indicates FD<0.2 approximates this

dtseries_pattern="task-rest_DCANBOLDProc_v4.0.0_Atlas.dtseries.nii"
FD=0.2
fd_set=no
SK_FLAG=""
rm_OUTLIER=no
MIN_FLAG=""
z_xfrm=no

while getopts ":d:f:i:k:L:l:m:o:R:r:xz" opt; do
    case $opt in
        d)
            dtseries_pattern="${OPTARG}" ;;
        f)
            FD=${OPTARG}
            fd_set=yes ;;
        i)
            input=${OPTARG} ;;
        k)
            sk=${OPTARG}
            SK_FLAG="--smoothing_kernel ${sk}" ;;
        L)
            L_ROI=${OPTARG} ;;
        l)
            l_rois=${OPTARG} ;;
        m)
            minutes=${OPTARG}
            MIN_FLAG="--minutes ${minutes}" ;;
        o)
            outdir=${OPTARG} ;;
        R)
            R_ROI=${OPTARG} ;;
        r)
            r_rois=${OPTARG} ;;
        x)
            rm_OUTLIER=yes
            OUTLIER_FLAG="--remove-outliers" ;;
        z)
            z_xfrm=yes ;;
        \?)
            echo "Invalid option: -${OPTARG}" >&2
            exit 1
            ;;
        :)
            echo "Option -${OPTARG} requires an argument." >&2
            exit 1
            ;;
    esac
done

# sub=$(echo "${input}" | grep -o "sub-[A-Za-z0-9]*")
# ses=$(echo "${input}" | grep -o "ses-[A-Za-z0-9]*")
tempdir=${outdir}

echolog(){
    file=${tempdir}/info.txt
    # touch ${file}
    echo -e "${1}" | tee -a "${file}"
}

# Collapse l/r rois and run each only once
# Keep separate in case we ever need them for something I guess, probably could
## have collapse as part of the arg but oh well
all_rois=$(echo "${l_rois} ${r_rois}" | tr -sc '[:digit:]' '\n' | sort -ug | \
            tr '\n' ' ')

echo    "----------------"
echolog "Input directory:\t${input}"
echolog "Output directory:\t${tempdir}"
echolog "MCR cache:\t\t${MCR_CACHE_ROOT}"
echolog "RH ROI file:\t\t${R_ROI}"
echolog "LH ROI file:\t\t${L_ROI}"
echo
if [[ ${fd_set} == "yes" ]] ; then
    echolog "FD threshold:\t\t${FD}"
else
    echolog "FD threshold:\t\t${FD} (default)"
fi
echolog "Smoothing kernel:\t${sk}"
echolog "Outlier removal:\t${rm_OUTLIER}"
echolog "Minimum data minutes:\t${minutes}"
echolog "ROI all_rois:\t\t${all_rois}"
echo    "----------------"
echo

if [ ! -d "${input}" ] ; then
    echo "ERROR: Input \"${input}\" doesn't exist/is not a directory, exiting."
    exit 1
fi

for i in ${L_ROI} ${R_ROI} ; do
    if [ ! -e "${i}" ] ; then
        echo "ERROR: ROI file \"${i}\" doesn't exist, exiting."
        exit 1
    fi
done

# Create output directory and exit if unsuccessful
mkdir -p "${tempdir}" || (echo "Unable to create tempdir ${tempdir}" && exit 1)

# Check at least one ROI given
n_all_rois=$(echo "${all_rois}" | wc -w)
if (( n_all_rois == 0 )) ; then
    echo "Must provide at least one ROI index"
    exit 1
else
    echo "Found ${n_all_rois} ROIs"
fi

echo "Looking for dtseries in ${input}, pattern = ${dtseries_pattern}"
dtseries=$(find "${input}" -name "${dtseries_pattern}")

echo    "dtseries:"
echo -e "\t${dtseries}"

# Check dtseries exists
if [ -e "${dtseries}" ] ; then
    TR=$(wb_command -file-information -only-step-interval "${dtseries}")
    echo -e "\tTR: ${TR}\n"
else
    echo "MISSING dtseries: ${dtseries}"
    exit 1
fi

################################################################################
# Create custom ptseries

labelfile=${tempdir}/session.dlabel.nii
ptseriesfile=${tempdir}/session.ptseries.nii

# Apply labels
wb_command -cifti-create-dense-from-template \
    "${dtseries}"    \
    "${labelfile}"   \
    -label           \
        CORTEX_LEFT  \
        "${L_ROI}"   \
    -label           \
        CORTEX_RIGHT \
        "${R_ROI}"

# Create ptseries
wb_command -cifti-parcellate \
    "${dtseries}"     \
    "${labelfile}"    \
    COLUMN            \
    "${ptseriesfile}" \
    -method MEAN      \
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

# roi_map=Power

# dt/ptseries
readlink -f "${dtseries}"     > "${dtseries_conc}"
readlink -f "${ptseriesfile}" > "${ptseries_conc}"
# echo "${dtseries_conc} ${ptseries_conc}"

# Locate surface giftis (includes subject id)
# Use these globs to find files named different, the "L[^R]" pattern attempts
# to isolate the hemi label separately from the "fsLR32k" string
## Then grep checks for MNI space (alt in name or dir label) and 32k
find "${input}/" -name "*L[^R]*midthickness*.surf.gii"  | \
    grep "MNI" | grep "32k"                             > \
    "${lmt_conc}"

if [ ! -s ${lmt_conc} ] ; then
    echo "No left midthickness found, exiting"
    exit 1
fi

find "${input}/" -name "*[^L]R[._]*midthickness*.surf.gii"  | \
    grep "MNI" | grep "32k"                                 > \
    "${rmt_conc}"

if [ ! -s ${rmt_conc} ] ; then
    echo "No right midthickness found, exiting"
    exit 1
fi

# Motion mat file
# Copy motion mat file locally to avoid seed mapper writing to input dir
# echo "${input}/files/DCANBOLDProc_v4.0.0/analyses_v2/motion/task-rest_power_2014_FD_only.mat" > \
#     "${motion_conc}"
motion_mat=$(find "${input}/" -name "sub-*_task-rest_*.mat"   | \
                grep -v "filteredwithoutliers")

if [ -z "${motion_mat}" ] ; then

    echo "!!!"
    echo "WARNING: No motion mat found, automatically not doing this."
    echo "         Add motion mat file if needing done."
    echo "!!!"

    MOTION_FLAG=""

else

    local_mat_file="${tempdir}/motion.mat"
    cp "${motion_mat}" "${local_mat_file}"
    readlink -f "${local_mat_file}" > "${motion_conc}"

    MOTION_FLAG="--motion ${motion_conc}"

fi

################################################################################
# Run

echo
echo "Seed mapping"
echo "------------"
echo -e "WB:\t$(which wb_command)"
echo -e "MRE:\t${mre}"
echo "Seed map wrapper: ${seed_map_wrapper}"
echo

# echo \
output=${tempdir}/seedmaps
mkdir -p "${output}"

for i in ${lmt_conc} ${rmt_conc} ${dtseries_conc} ${ptseries_conc} ; do
    if [ ! -e "${i}" ] ; then
        echo "Important file (${i}) doesn't exist"
        exit 1
    fi
done

run_and_z () {

    seed=${1}

    cmd="
        python3 ${seed_map_wrapper}       \
            --mre-dir      ${mre}         \
            --wb_command   ${wb_command}  \
            --source       ${source}      \
            --fd-threshold ${FD}          \
            --left         ${lmt_conc}    \
            --right        ${rmt_conc}    \
            ${MOTION_FLAG}                \
            --output       ${output}      \
            ${SK_FLAG}                    \
            ${OUTLIER_FLAG}               \
            ${MIN_FLAG}                   \
            ${TR}                         \
            ${dtseries_conc}              \
            ${ptseries_conc}              \
            ${seed}
        "

    # Echo cmd to log and then run
    echo "${cmd}" | tr -s "[:blank:]" " "
    ${cmd}

    # if [ ! -z ${MIN_FLAG} ] ; then
    #     find ${tempdir}/seedmaps -name ""

    file_created=$(find "${tempdir}" \
                    -name "*task-rest_*_ROI${seed}.dscalar.nii")

    if [ "${file_created}" == "" ] ; then
        echo "Output from seedmap not created, exiting"
        exit 1
    fi

    # new_file="${file_created//_ROI/_roi-}"
    new_file=$(echo "${file_created}" | sed 's/_ROI/_roi-/')
    mv "${file_created}" "${new_file}"
    echo "Created:  ${new_file}"
    echo

    if [ ${z_xfrm} == "yes" ] ; then

        z_dscalar="${new_file%.dscalar.nii}_Z.dscalar.nii"

        if [ ! -e "${z_dscalar}" ] ; then

            # equation from Z14
            wb_command -cifti-math                           \
                '(0.5*ln((1+r)/(1-r)))'                      \
                "${z_dscalar}" \
                -var r "${new_file}"

            echo

        fi

    fi

}

for i in ${all_rois} ; do
    run_and_z "${i}"
done
wait
