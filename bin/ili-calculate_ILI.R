# Get command-line arguments

args <- commandArgs(trailingOnly = TRUE)
the_file <- args[1]
size <- args[2]

# Declare function

ILI_from_txt <- function(frame, size = NA) {

  # Ensure input contains correct columns
  if (!all(c("nrh", "LI") %in% colnames(frame)))
    stop("Input frame must contain columns nrh and LI!")

  # Get size if necessary
  if (is.na(size)) {
    size <- max(frame$nrh)
    message(paste0("Setting size for ", the_file, " to max(nrh) [", size,
                   "] - this is imprecise."))
  } else {
    size <- as.numeric(size)
    message(paste0("Max size for ", the_file, " is ", size))
  }

  # Do analysis
  frame$p <- frame$nrh / size

  # Fit cubic model
  model <- lm(LI ~ 1 + p + I(p^2) + I(p^3), data = frame)

  # If missing values in input, cannot integrate
  if (sum(is.na(coef(model))) == 0) {

    # Convert to function and integrate. Range for integration is fixed to
    # [0, 1] when using p (0% NRH to 100% NRH)
    fun <- function(x) { sum(coef(model) * c(1, x, x^2, x^3)) }
    integral <- integrate(Vectorize(fun), lower = 0, upper = 1)
    result <- integral$value

  } else {
    result <- NA
  }

  return(result)

}

# Load data

frame <- read.csv(the_file)
frame$LI <-(frame$L - frame$R) / (frame$L + frame$R)

# Estimate, guessing at size from data
ili1 <- ILI_from_txt(frame, size)

cat(ili1, fill = TRUE)
