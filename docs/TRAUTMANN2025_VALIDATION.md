# Trautmann et al. (2025) public-data validation

## Product boundary

This work uses a published NHP Neuropixels dataset as an external acceptance
test for reusable NeuroEphys AI methods. It does not add a paper scraper, a
paper-specific wizard, or hard-coded panel logic to the product. MATLAB loading,
the authors' trial filters, and the paper-like validation layout remain in the
separate validation workspace.

## Sources and provenance

- Article: Trautmann et al., *Nature Neuroscience* 28, 1562-1575 (2025),
  [doi:10.1038/s41593-025-01976-5](https://doi.org/10.1038/s41593-025-01976-5).
- Public Fig. 7 source data/code: Stine et al. Zenodo record
  [7946011](https://zenodo.org/records/7946011), CC BY 4.0.
- Downloaded archive: `Stine et al_2023_Code_and_Data.zip`, 565,533,370 bytes.
- Verified MD5: `13d8995bf00160c332891c7abf8c3d1f` (matches the Zenodo record).
- The article's stated Zenodo DOI for Figs. 1-6 and 8,
  `10.5281/zenodo.14744139`, returned an unregistered/404 record during the
  2026-08-17 validation. Those panels are therefore not marked reproduced.

## Prespecified Fig. 7 validation

The validation retained completed dynamic-motion trials with finite coherence,
positive duration, and `trialType == 20`, matching the disclosed author script.
It used the author-supplied LIP Tin and SC unit indices, 1 ms bins, Gaussian
sigma of 25 ms, motion and saccade alignment, variable per-trial valid windows,
and per-trial motion baseline subtraction.

| Area | Source trials | Eligible trials | Available units | Selected units | NeuroEphys vs disclosed MATLAB kernel |
|---|---:|---:|---:|---:|---:|
| LIP | 2,818 | 1,797 | 191 | 17 | Pearson r = 0.998685 |
| SC | 3,396 | 1,859 | 16 | 10 | Pearson r = 0.998148 |

Agreement was evaluated on 120 deterministic trials per area and 48,359 LIP / 
46,629 SC finite trace points in the displayed motion-aligned interval. The
normalized RMSE was 0.101 reference SD for LIP and 0.115 reference SD for SC.
The small amplitude difference is consistent with the author's finite
plus/minus 50 ms sampled Gaussian kernel versus NeuroEphys AI's normalized
Gaussian filter.

## Reusable capabilities added

- Single-trial population binning and configurable Gaussian smoothing.
- Explicit per-trial validity masks for variable-duration behavior.
- Pooled-unit or per-trial baseline subtraction/z-scoring.
- Event/condition and brain-region unit selection in the desktop App.
- Peak-time, PCA-loading, or optional Rastermap population ordering.
- Ordered heatmap, single-trial, condition, and PCA trajectory views.
- Trial-held-out continuous-signal regression with configurable neural/target
  lag and repeated neuron-count scaling.
- Count, reference-rate, or trial/rate/lag-edge-normalized CCG.
- Interval/centered jitter correction, flank-SD or empirical inference,
  multiplicity control, spatial/region pair filters, and auditable pair caps.

## Interpretation limits

- Fig. 7 validation checks analysis implementation against an accessible public
  source dataset; it is not evidence that inaccessible Figs. 1-6/8 were
  reproduced.
- Significant jitter-corrected timing relationships are functional evidence,
  not proof of monosynaptic or anatomical connectivity.
- The external paper-specific validation script is not shipped as a core
  product workflow. Core methods remain data-source-agnostic and user-selectable.
