# Makefiles only update if the files the LHS relies on are newer than the
# 	output. Use this to detect if the container needs to be rebuilt or not

.PHONY: build

build: crossotope.sif

# crossotope.def and ili_manager are the top-level files; they rely on
#	everything in bin/, so include those too.
crossotope.sif: crossotope.def ili_manager.py \
		bin/analysis-cluster.sh bin/analysis-run_seedmap.sh \
		bin/rois_create_mirror.sh bin/rois_dscalar_to_surface.sh \
		bin/rois_permute_ROI.R bin/run-seedmap-on-dir.py
	singularity build \
		--fakeroot --fix-perms --force --writable-tmpfs \
		$@ $<
