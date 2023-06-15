#!/bin/bash

START=$(date '+%s')

if [ ${#} -eq 1 ] ; then
    def=${1}
    sif="${def//.def/.sif}"
else
    echo "Supply .def file path"
    exit 1
fi

# --force overwrites current version
singularity build \
    --fakeroot --fix-perms --force --writable-tmpfs \
    "${sif}" "${def}"

END=$(date '+%s')

sec=$(( END - START ))
min=$(echo "${sec} / 60" | bc -l)

echo "Build time: ${sec} sec. ($(printf %.2f "${min}") min)"

echo
du -hsc "${sif}"
