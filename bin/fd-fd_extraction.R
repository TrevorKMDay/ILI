suppressPackageStartupMessages(library(R.matlab))

args <- commandArgs(trailingOnly = TRUE)

if (length(args) %in% c(2, 3)) {
  mat_file <- args[1]
  FD <- args[2]
  param <- args[3]
} else if (length(args) == 0) {

  message("Usage: Rscript fd_extraction.R [mat file] [FD threshold] [param]

    FD threshold: Between [0, 0.5] in 0.01 steps
    param:
      1|TR
      2|frames  (remaining frames)
      3|sec     (remaining seconds)
      4|FD      (FD of remaining data)
    ")

  quit(save = "no")

}

mat <- readMat(mat_file)

# Possible FD values
steps <- seq(0, 0.5, by = 0.01)

if (FD < 0){
  stop("FD < 0 is nonsensical")
} else if (FD > 0.5) {
  stop("Cannot handle FD > 0.5")
} else {

  if (!(FD %in% steps)) {
    # FD is only taken out to two places
    message(paste("Rounding", FD, "to", round(FD, 2)))
    FD <- round(FD, 2)
  }

}

which_df <- match(FD, steps)
the_dat <- mat$motion.data[[which_df]][[1]]

names <- dimnames(the_dat)[[1]]

if ("epi.TR" %in% names) {
  tr <- which(names == "epi.TR")
  TR <- the_dat[[2]][1, 1]
} else {
  TR <- NA
}

r_f <- which(names == "remaining.frame.count")
r_s <- which(names == "remaining.seconds")
r_mfd <- which(names == "remaining.frame.mean.FD")

remaining_frames <- the_dat[[r_f]][1, 1]
remaining_seconds <- the_dat[[r_s]][1, 1]
remaining_mean_FD <- round(the_dat[[r_mfd]][1, 1], 4)

if (is.na(param)) {

  # message(paste("TR:                    ", TR))
  # message(paste("Remaining frames:      ", remaining_frames))
  # message(paste("Remaining seconds:     ", remaining_seconds))
  # message(paste("FD of remaining frames:", round(remaining_mean_FD, 3)))

  cat("TR, frames, seconds, mean FD", fill = TRUE)
  cat(paste(TR, remaining_frames, remaining_seconds, remaining_mean_FD,
            sep = ", "),
      fill = TRUE)

} else {

  if (param %in% c(1, "TR")) {
    message(TR)
  } else if (param %in% c(2, "frames")) {
    message(remaining_frames)
  } else if (param %in% c(3, "sec")) {
    message(remaining_seconds)
  } else if (param %in% c(4, "FD")) {
    message(round(remaining_mean_FD, 2))
  } else {
    stop("Unrecognized parameter")
  }

}
