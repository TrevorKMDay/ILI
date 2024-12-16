import os
import re
import subprocess as sp
import pandas as pd
import pprint as pp


def write_csv(df, csv_file):

    # Write to CSV without index column and then remove '#' from header row
    df.to_csv(csv_file, index=False)

    print(f"{csv_file} saved!")


def calculate_ILI(directory, output_file, sizes=None):

    # TO DO: Don't overwrite existing files
    # TO DO: .csv addition isn't working

    # Find all files in directory
    files = [f for f in os.listdir(directory)
             if os.path.isfile(os.path.join(directory, f))]

    # Reduce to CSV files
    csv_files = [os.path.join(directory, f) for f in files if ".csv" in f]

    print(f"Found {len(csv_files)} CSV files")

    results = []

    for csv in csv_files:

        # Get size of ROI by identifying ROI from the filename and looking it
        #   up.
        # csv_basename = os.path.basename(csv).replace("_results.csv", "")

        # Find `roi-foo`` label in filename, if not, fall back to automatic
        #   detection.
        if "roi-" in csv:
            roi_label = re.search(r'roi-[^_]*', csv)[0]
            roi_name = roi_label.replace("roi-", "")

        else:
            print(f"Missing BIDS-like `roi-foo` in {csv}, cannot use this "
                  "to find size. Size will be set automatically.")

        if sizes is not None and roi_name in sizes.keys():
            size = sizes[roi_name]
            result = sp.run(["Rscript", "bin/ili-calculate_ILI.R", csv,
                             str(size)],
                            stdout=sp.PIPE)
        else:
            # If roi_name not found in json file, fall back
            print(f"Size for roi {roi_name} was not found, falling back to "
                  "automatic detection.")

            result = sp.run(["Rscript", "bin/ili-calculate_ILI.R", csv],
                            stdout=sp.PIPE)

        result_clean = result.stdout.decode('utf-8').replace("\n", "")
        ili, sec = [x for x in result_clean.split(",")]

        # Clean up file name
        shortname = str.replace(os.path.basename(csv), ".csv", "")
        print(shortname)

        # Build up dataframe
        results.append([shortname, ili, sec])

    df = pd.DataFrame(results)
    df.columns = ["file", "ILI", "seconds"]

    # Append .csv to output file if not supplied
    output_file = f"{output_file}.csv" \
                  if re.search(".csv", output_file) is None \
                  else output_file

    # My custom CSV wrapper
    write_csv(df, output_file)
