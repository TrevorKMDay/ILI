#!/bin/bash

START=$(date '+%s')

# --force overwrites current version
singularity build \
    --fakeroot --fix-perms --force \
    my_img.sif my_img.def

END=$(date '+%s')

sec=$(( END - START ))
min=$(echo "${sec} / 60" | bc -l)

echo "Build time: ${sec} sec. ($(printf %.2f "${min}") min)"

echo
du -hsc my_img.sif
