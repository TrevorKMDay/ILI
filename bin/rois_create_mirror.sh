#!/bin/bash

wb_command="${1}"
input=$(readlink -f "${2}")
outfile=${3}

# Add wb_command to path
wb_command_dir="${wb_command}"
export PATH="${wb_command_dir}:${PATH}"

echo "wb_command: $(which wb_command)"

tempdir=$(dirname "${input}")
basename=$(basename "${input}")
suffix=$(echo "${basename}" | grep -o "[.][a-z]*[.]nii")
prefix=$(echo "${basename}" | sed "s/${suffix}//")

# Temporary cifti
temp_cifti=$(mktemp "/tmp/${prefix}_XXXXX${suffix}")
source_lh=$(mktemp "/tmp/${prefix}_XXXXX.lh.func.gii")
source_rh=$(mktemp "/tmp/${prefix}_XXXXX.rh.func.gii")

# Create files in tempdir
wb_command -cifti-separate \
    "${input}"                          \
    COLUMN                              \
    -metric CORTEX_LEFT  "${source_lh}" \
    -metric CORTEX_RIGHT "${source_rh}" & \
    echo "Split complete"

# Apparently wb_command -cifti-separate exits before it's done writing to disk
wait

# Recombine
# Send wrong-metric-label errors to /dev/null
wb_command -cifti-create-dense-from-template \
    "${input}"                          \
    "${temp_cifti}"                     \
    -metric CORTEX_LEFT  "${source_rh}" \
    -metric CORTEX_RIGHT "${source_lh}"  2>/dev/null & \
  echo "Flip complete (${temp_cifti})"

# As above
wait

# If an explicit file name was given, save to that
if [ -z ${outfile+x} ] ; then
    mv "${temp_cifti}" "${tempdir}/${prefix}_L2R${suffix}"
else
    echo "  ... moving to ${outfile}"
    mv "${temp_cifti}" "${outfile}"
fi
