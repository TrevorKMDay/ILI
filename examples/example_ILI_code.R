setwd("~/crossotope_mapping/examples")

# I use tidyverse, you don't have to
library(tidyverse)

# Load function
source("ILI_from_txt.R")

# Read data

V2 <- read_csv("results_V2.csv") %>%
  mutate(
    LI = (L - R) / (L + R)
  )

# Estimate, guessing at size from data
ili1 <- ILI_from_txt(V2)

# True size based on Maryam's table
ili2 <- ILI_from_txt(V2, size = 622)

(ili1 - ili2) / ili2 # This gives the estimate at 6% error [for this one ROI]
