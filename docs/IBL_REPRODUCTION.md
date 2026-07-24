# IBL Brain-Wide Map reproduction path

NeuroFlow uses the 2025 IBL Brain-Wide Map as a public, large-scale reference
workflow. It does not claim pixel-identical reproduction of every panel. Each
implemented view states its input fields, alignment window, statistical unit,
cross-validation method, and relationship to the paper.

Primary sources:

- Paper: https://www.nature.com/articles/s41586-025-09235-0
- Release: https://docs.internationalbrainlab.org/notebooks_external/2025_data_release_brainwidemap.html
- ONE download guide: https://docs.internationalbrainlab.org/notebooks_external/data_download.html

## Implemented views

| NeuroFlow view | Required ALF fields | Related paper analysis |
|---|---|---|
| Psychometric curve | contrastLeft, contrastRight, choice | Figure 1 behavior |
| Reaction time | stimOn_times, firstMovement_times | Figure 1 behavior |
| Raster and PETH | spikes.times, spikes.clusters, stimOn_times | Figure 4 stimulus response |
| Time-resolved decoding | trial labels and binned population firing | Figure 4 decoding |
| Population PCA trajectory | condition-averaged population firing | Figure 4 trajectories |
| Trajectory distance | PCA trajectory pair | Figure 4 distance |

The application also reproduces the paper's general validation logic: held-out
cross-validation, a shuffled-label null distribution, effect sizes, confidence
intervals, and Benjamini-Hochberg correction. It does not automatically make
claims about neural coding from a significant classifier.

## Download a processed example

The default downloader fetches the official 24 MB BWM aggregate trials table
from the public AWS bucket. It deliberately does not download raw Neuropixels
AP files. Add `--full-session` to use ONE for processed trials and spikes.

```powershell
python scripts/download_ibl_example.py --cache ibl_cache
```

In NeuroFlow, choose **Import data > IBL public data** and select the printed
Parquet file. For neural panels, run the command with `--full-session` and
select the printed `alf` folder. Keep the IBL paper and AWS dataset citation.
