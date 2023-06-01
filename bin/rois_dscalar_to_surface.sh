#!/bin/bash

if [ ${#} -eq 2 ] ; then
    wb_cmd=$(readlink -f "${1}")
    directory=${2}
else
    echo "Supply directory"
    exit 1
fi

# Create label file that to apply to ROIs
label_file="/roi_outputs/1label.txt"

echo \
"bilateral_ROI
1 255 0 0 255" > "${label_file}"

# wb_cmd=workbench/1.4.2/workbench/bin_rh_linux64/wb_command

################################################################################

# cd into directory
cd "${directory}" || exit

# For every dscalar, create a dlabel if both the dlabel file and the label
# gifti don't exist (if the label gifti exists, the whole process is done)
for dscalar in *.dscalar.nii ; do

    # Haha
    if [[ ${dscalar} == "flipped_roi.dscalar.nii" ]] ; then continue ; fi

    dlabel=${dscalar//scalar/label}
    bn=${dscalar%.dscalar.nii}

    if [ ! -e "${dlabel}" ] ; then

        ${wb_cmd} -cifti-label-import \
            "${dscalar}"    \
            "${label_file}" \
            "${dlabel}"     \
            -discard-others

        echo "Done with ${dlabel}"

    fi

    # break

done

echo "Done with dlabeling ${directory}"

# For every dlabel that exists, covert to surface gifti if that doesn't
# exist already
for dlabel in $(find . -name "*_nrh-[0-9]*_ix-[0-9]*.dlabel.nii") ; do

    # echo $dlabel
    bn=${dlabel%.dlabel.nii}
    if [ ! -e "${bn}_L.label.gii" ] ; then

        ${wb_cmd} -cifti-separate \
            "${dlabel}" \
            COLUMN      \
            -label CORTEX_LEFT  "${bn}_L.label.gii" \
            -label CORTEX_RIGHT "${bn}_R.label.gii"

        echo Done with "${bn} label gifti"

    fi

done

echo "Done with label giis for ${directory}"

