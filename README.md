# ILI

Trevor Day // day00096@umn.edu

Code to create the Singularity container for ILI ROI creation and processing.

# Config file

To make it the command line options simpler to use, the options to the 
seedmap wrapper are included in a configuration JSON file, e.g.

    {
        "fd_threshold":         0.2,    # Threshold in mm
        "smoothing_kernel":     0,      # Smoothing kernel in mm (0=none)
        "max_minutes":          10,     # Minutes to sample from dtseries
        "remove_outliers_yn":   1,      # Whether to remove outliers (0/1)
        "z_xfrm_yn":            1       # Whether to Z-transform results (0/1)
    }

Default values are those listed in example above.