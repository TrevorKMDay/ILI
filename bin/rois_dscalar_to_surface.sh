#!/bin/bash



if [ ${#} -eq 1 ] ; then
    directory=${1}
else
    echo "Supply directory"
    exit 1
fi

# Create label file that to apply to ROIs
echo \
"bilateral_ROI
1 255 0 0 255" > 1label.txt

label_file="$(pwd)/1label.txt"

################################################################################

# cd into directory
cd "${directory}" || exit

# For every dscalar, create a dlabel if both the dlabel file and the label
# gifti don't exist (if the label gifti exists, the whole process is done)
for dscalar in *.dscalar.nii ; do

    dlabel=${dscalar//scalar/label}
    bn=${dscalar%.dscalar.nii}

    if [ ! -e "${dlabel}" ] ; then

        wb_command -cifti-label-import \
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

        wb_command -cifti-separate \
            "${dlabel}" \
            COLUMN      \
            -label CORTEX_LEFT  "${bn}_L.label.gii" \
            -label CORTEX_RIGHT "${bn}_R.label.gii"

        echo Done with "${bn} label gifti"

    fi

done 

echo "Done with label giis for ${directory}"

