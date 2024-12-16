import os
import sys
import re
import random
import glob
import numpy as np
import subprocess as sp


def analyze_session(dtseries_file, motion_file,
                    roi_dir, n, config, matlab, mre_dir, label,
                    l_midthick_file=None, r_midthick_file=None,
                    halfway=False, cwd="."):

    """
    Given a session, create the table of LI per seed laterality

    :param str dtseries_file: The path to the dtseries file (ends in
                                dtseries.nii).
    :param str motion_file: The path to the motion file (ends in .mat)
    :param str roi_dir: The path to the directory containing the crossotopes
                        (created with roi subcommand)
    :param int n: The number of subsamples to take
    :param list config: The config file read in to python.
    :param str matlab: The path to the MATLAB executable.
    :param str mre_dir: The path to the MATLAB Runtime directory.
    :param str l_midthick_file: The path to the left midthickness file (only if
                                smoothing.)
    :param str r_midthick_file: As above.

    """

    print("\n=== Running analysis flow ... ===")

    os.chdir("/tmp/")
    os.close(os.open("file.txt", os.O_CREAT))

    if os.path.exists("file.txt"):
        print("INFO: Temp file system working.")
        os.remove("file.txt")

    # TO DO: Check matlab is properly executable

    # Check input files
    # os.path.realpath resolves relative paths, symlinks the user gives it

    if ".dtseries.nii" in dtseries_file:
        # Simplify legibility of code
        dtseries = os.path.realpath(dtseries_file)
        print(f"INFO: dtseries is:\n\t{dtseries_file}")
    else:
        sys.exit("ERROR: First input should be a .dtseries.nii file")

    if ".mat" in motion_file:

        # Simplify legibility of code
        motion_file = os.path.realpath(motion_file)
        print(f"INFO: Motion file is:\n\t{motion_file}")

        # sp.run(["Rscript", "{args.cwd}/bin/fd_extraction.R", motion_file,
        #         config["fd_threshold"]],
        #        stdout="/output/data_info.txt")

        # exit()

    elif motion_file == "NONE":
        motion_file = "NONE"
        print(f"INFO: Motion file is:\n\t{motion_file}")
    else:
        sys.exit("ERROR: Second input should be a .mat file or NONE")

    # Check midthickness files if given
    if l_midthick_file is not None and ".surf.gii" in l_midthick_file:
        # Simplify legibility of code
        l_midthick_file = os.path.realpath(l_midthick_file)
        print(f"L midthick is:\n\t{l_midthick_file}")
    elif l_midthick_file is not None and ".surf.gii" not in l_midthick_file:
        sys.exit("ERROR: Input session file 2 should be a .surf.gii file")

    if r_midthick_file is not None and ".surf.gii" in r_midthick_file:
        # Simplify legibility of code
        r_midthick_file = os.path.realpath(r_midthick_file)
        print(f"L midthick is:\n\t{r_midthick_file}")
    elif r_midthick_file is not None and ".surf.gii" not in r_midthick_file:
        sys.exit("ERROR: Input session file 2 should be a .surf.gii file")

    # Load in ROIs
    if roi_dir is not None:

        rois = [f for f in os.listdir(roi_dir) if
                os.path.isfile(os.path.join(roi_dir, f))]

        # print(rois)
        # print([re.findall(r"nrh-[0-9]+", f)[0] for f in rois
        #         if ".label.gii" in f])

        roi_labels = [f for f in rois if ".label.gii" in f]

        # Extract # of unique nrh values
        size = len(set([re.findall(r"nrh-[0-9]+", f)[0] for f in roi_labels]))

        if size < n:
            print(f"Requested # of samples ({n}) is smaller than size, "
                  f"({size}), setting n to {size}.")
            n = size

        indices = len(set([re.findall(r"ix-[0-9]+", f)[0] for f in
                           roi_labels]))

        # Find the first index to get the width for zero-padding
        index1 = [re.findall(r"ix-[0-9]+", f)[0] for f in roi_labels][0]
        # Returns "ix-\d+", don't count "ix-"
        ix_zpad = len(index1) - 3

        print(f"Found {size} ROIs with {indices} copies each.")

        if not halfway:

            # Select n ratios from those available
            sizes_to_use = random.sample(list(range(1, size + 1)), n)
            sizes_to_use.sort()

        else:

            sizes_to_use = list(range(round(size / 2), round(size / 2) + 1))

        print(f"Using sizes {sizes_to_use}")

        # For each size selected, choose an index to use for that ROI
        indices_to_use = [int(random.uniform(1, indices)) for i in
                          sizes_to_use]

        # TO DO: zfill assumes sizes of exactly 3 for size and 2 for index
        sizes_to_use_str = [str(i).zfill(3) for i in sizes_to_use]
        indices_to_use_str = [str(i).zfill(ix_zpad) for i in indices_to_use]

        # Zip ratios, indices
        ROIs_to_use_str = zip(sizes_to_use_str, indices_to_use_str)

        # Structure (nrh, ix, [L, R])
        # Find these files in the original directory
        files_to_use = [glob.glob(f"{roi_dir}/*_nrh-{nrh}_ix-{ix}_?.label.gii")
                        for nrh, ix in ROIs_to_use_str]

        # Get full path here before doing nonsense with temporary directories
        files_to_use = [[os.path.realpath(x) for x in y] for y in files_to_use]

        # Store numeric values, file destination
        ROIs = zip(range(0, n), sizes_to_use, indices_to_use, files_to_use)

    else:
        # ROIs need to be supplied for session flow
        sys.exit("ERROR: Directory of ROIs required")

    # Create empty array with size n(x)4: NRH, IX, L, R
    results = np.zeros((n, 4), dtype=np.int64)

    for n, nrh, ix, files in ROIs:

        if "_L.label.gii" in files[0]:
            l_roi_file = os.path.realpath(files[0])
            r_roi_file = os.path.realpath(files[1])
        elif "_L.label.gii" in files[1]:
            l_roi_file = os.path.realpath(files[1])
            r_roi_file = os.path.realpath(files[0])

        # pp.pprint(files)
        # pp.pprint([l_roi_file, r_roi_file])

        # TO DO: Don't hardcode this width
        nrh_zpad = str(nrh).zfill(3)

        # Matlab function ciftiopen() seems to want to run "-cifti-convert
        #   -to-gifti-ext" writing the output to the working directory (/home).
        # This doesn't work in a container, so chdir to the filesystem /tmp
        temp_dir_name = f"/tmp/{label}_{nrh_zpad}"

        print(f"Working directory is: {temp_dir_name}")
        os.makedirs(temp_dir_name)

        # Params
        #   1: Zero-padded NRH
        #   2-3: Where to find Matlab
        #   4-5: L/R ROI files
        #   6-9: session dtseries, l/r midthickness, motion
        #   10: FD; 11: smoothing kernel; 12: rm outliers?; 13: minutes;
        #   12: Z-transformation?
        # Note: sp.run seems to require all args to be strings

        rsm_cmd = [f"{cwd}/bin/analysis-run_seedmap.sh",
                   nrh_zpad,
                   matlab, mre_dir,
                   l_roi_file, r_roi_file,
                   dtseries,
                   str(l_midthick_file), str(r_midthick_file),
                   motion_file,
                   str(config['fd_threshold']),
                   str(config['smoothing_kernel']),
                   str(config['remove_outliers_yn']),
                   str(config['max_minutes']),
                   str(config['z_transform_yn']),
                   temp_dir_name]

        # pp.pprint(rsm_cmd)

        p = sp.run(rsm_cmd, check=False)

        sp.run(["ls", f"{temp_dir_name}/"])
        sp.run(["ls", f"{temp_dir_name}/seedmaps/"])

        seedmap_rc = p.returncode
        if seedmap_rc == 100:
            print("\nERROR: Output from seedmap not created!\n"
                  "Possibly too few good frames.")
            sys.exit(100)

        # setting check=True causes python to exit if this command fails
        # useful for dev, but not prod
        cluster = sp.run([f"{cwd}/bin/analysis-cluster.sh",
                          temp_dir_name,
                          str(config["cluster_value_min"]),
                          str(config["cluster_surf_area_min"])],
                         check=False,
                         stdout=sp.PIPE, stderr=sp.STDOUT,
                         universal_newlines=True)

        # Log cluster info
        print(cluster.stdout)

        result1 = re.findall(r'RESULT: \[\d+ \d+\]', cluster.stdout)[0]
        result2 = result1.replace("RESULT: ", "")
        result3 = re.sub(r'[\[\]]', '', result2).split(' ')

        # Add results to array
        results[n, 0] = nrh
        results[n, 1] = ix
        results[n, 2] = int(result3[0])
        results[n, 3] = int(result3[1])

        # print([nrh, ix, result3])

        # break

    return results
