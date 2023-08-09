#!/bin/bash

START=$(date '+%s')

if [ ${#} -eq 1 ] ; then
    def=${1}
    sif="${def//.def/.sif}"
else
    echo "Supply .def file path"
    exit 1
fi

ver=$(grep "^ *VERSION" "${def}" | sed "s/^ *VERSION //")
echo "Version is ${ver}"

if grep -q "VERSION = \"${ver}\"" ili_manager.py ; then
    echo "Version label OK, building ..."
else
    echo -n "Version label does not match in ili_manager.py, replacing and "
    echo    "continuing to build."
    sed -i "s/VERSION = .*/VERSION = \"${ver}\"/" ili_manager.py
fi

# Blank line for legibility
echo

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
