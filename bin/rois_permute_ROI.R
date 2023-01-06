suppressPackageStartupMessages(library(tidyverse))
library(ciftiTools)

# Setup =====

args <- commandArgs(trailingOnly = TRUE)

# Input
wb_cmd <- args[1]
left_cifti_path  <- args[2]
right_cifti_path <- args[3]
n_permutations <- args[4]

# Output
outdir <- args[5]
outpfx <- args[6]

ciftiTools.setOption("wb_path", wb_cmd)

dir.create(outdir, showWarnings = FALSE, recursive = TRUE)

###############################################################################

hemi_size <- c("left" = 29696, "right" = 29716)

# Read in cifti data
left_cifti <- read_cifti(left_cifti_path)
right_cifti <- read_cifti(right_cifti_path)

# Which values in the cifti matrix are part of the ROI?
left_indices  <- which(left_cifti$data$cortex_left > 0)
right_indices <- which(right_cifti$data$cortex_right > 0)

size <- length(left_indices)

set.seed(55455)

message(paste("Size:", size))
message(paste(size * as.numeric(n_permutations), 
              "ROIs to create. This can take some time."))

for (i in 1:size) {

  for (j in 1:n_permutations) {

    out_file <- paste0(outdir, "/", outpfx, "_nrh-", str_pad(i, 3, "left", 0),
                        "_ix-", str_pad(j, 2, "left", 0), ".dscalar.nii")

    if (!file.exists(out_file)) {

      new_cifti <- left_cifti

      # These are the indexes of the ROI to zero in the L hemisphere and add to
      # the R hemisphere
      indexes_to_swap <- sample(1:size, size = i)

      # Remove values from LH
      new_cifti$data$cortex_left[left_indices[indexes_to_swap]] <- 0
      # Add to RH
      new_cifti$data$cortex_right[right_indices[indexes_to_swap]] <- 1

      # Set values to only 0/1 in LH
      new_cifti$data$cortex_left[new_cifti$data$cortex_left > 0] <- 1

      # message(paste(i, j))
      message(out_file)
      write_cifti(new_cifti, out_file, verbose=FALSE)

    }

  }

}