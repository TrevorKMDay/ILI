# ILI

Trevor Day // day00096@umn.edu

Code to create the Singularity container for ILI ROI creation and processing.

# Config file

To make it the command line options simpler to use, the options to the 
seedmap wrapper are included in a configuration JSON file, e.g.

    {
        # Values for seedmap wrapper

        "fd_threshold":         0.2,    # Threshold in mm
        
        "smoothing_kernel":     0,      # Smoothing kernel in mm 
                                        #   0 = none

        "max_minutes":          10,     # Minutes to sample from dtseries
                                        #   0 = no limit
        
        "remove_outliers_yn":   1,      # Whether to remove outliers (0/1)
        
        "z_transform_yn":       1       # Whether to Z-transform results (0/1)

        # Thresholds for determining laterality
        
        "cluster_value_min":        0.4     # Value to threshold map at

        "cluster_surf_area_min":    10,     # Minimum cluster size to keep 
                                            #   (mm^2)
    }   

Default values are those listed in example above. FYI no comments in actual
JSON files.

## Minutes

`dtseries` files with less than 10 minutes of good data will be run; the output
files have a different name than those that met the criterion.

Files with less than 30 s of good data will not be run at all.

## Z-threshold

Currently, the no-transformation option isn't complete. Keep it set to 1. 
