Statistics, machine learning, and scientific limits
===================================================

Statistical design starts with the biological sampling unit. Spikes, units,
sessions, and animals occupy different levels and cannot be treated as
independent copies without justification.

Statistical suite
-----------------

The workbench provides paired and unpaired tests, nonparametric alternatives,
bootstrap intervals, permutation tests, effect sizes, multiplicity correction,
diagnostics, and mixed-effects support when the project contains the required
hierarchy.

Before running a test, define:

* the unit of observation;
* pairing or repeated measurements;
* baseline and response windows;
* the family of comparisons;
* animal and session identifiers;
* exclusions decided before seeing the result.

Report effect sizes and uncertainty with p-values. A non-significant result is
reported as such; the software does not convert it into evidence for encoding.

Decoding
--------

Classification and regression operate on trial/event-level features. The
output includes cross-validated performance, confusion matrix, ROC/F1 where
applicable, label-permutation evidence, time-resolved performance, population
trajectories, and feature importance.

Use grouped splitting when samples from the same session or animal could appear
in both training and test sets. Fit scaling, feature selection, and dimensional
reduction inside each training fold. Inspect class balance and the full null
distribution.

Interpreting the figure
-----------------------

The confusion matrix reports counts and row-normalized percentages. The
permutation panel marks observed performance and chance level. A high training
score without held-out evidence is not shown as a scientific result.

Machine-learning performance establishes predictive information under the
specified validation design. Causality, mechanism, and generalization to new
animals require additional evidence.

Multi-session and multi-animal studies
--------------------------------------

A project still represents one recording session. After completing event-aligned
analysis in each session, choose **File → Multi-session study…** and add the relevant
``neuroflow_project.json`` manifests. Every row needs a biological animal ID and a
unique session ID; an electrode, region, or channel group is not an animal.

The Study workspace preserves the hierarchy ``trial → session → animal`` and provides:

* logistic regression, linear/RBF SVM, shrinkage LDA, and random forest with entire
  sessions or animals held out;
* scaling fitted inside each training fold;
* group-bootstrap intervals, within-group label permutations, and per-held-out-group
  performance;
* session-level condition summaries and, when enough animals are available, a linear
  mixed model with an animal random intercept and session variance component;
* fixed-dimensional population-distribution features, so Unit 7 in two sessions is
  never silently treated as the same neuron;
* descriptive latent dynamics: PCA followed by a regularized linear state-transition
  fit with trajectories, explained variance, and transition fit quality.

LDA (linear discriminant analysis) is a supervised classifier. The separate latent-
dynamics analysis is neither LDA nor a deep generative model. It summarizes low-
dimensional trajectories and approximate linear evolution; it does not establish a
dynamical mechanism or causality.

Recommended order
~~~~~~~~~~~~~~~~~

1. Import, curate Units, align behavior/TTL, and run identical event windows in each session.
2. Check condition names, baseline/response windows, and time bins across sessions.
3. Create a Study and verify animal/session identities and exclusions.
4. Inspect coverage and session-level effects, then start with an animal-held-out linear baseline.
5. Keep the same grouped design when comparing nonlinear models and inspect the permutation null.
6. Interpret latent trajectories as population-state descriptions, not replacements for
   hierarchical inference or independent validation.

With one animal, the application falls back to session-held-out validation and explicitly
withholds cross-animal inference. Cell identities are unmatched unless separate tracking
evidence is supplied; “unmatched” is the safe default.

Python and command line
~~~~~~~~~~~~~~~~~~~~~~~

The Python package exports ``StudyState``, ``add_project``,
``run_multi_session_analysis``, and ``run_latent_dynamics``. The CLI can create,
inspect, and run a Study:

.. code-block:: powershell

   neuroephys study-create D:\Study01 --name "Learning cohort"
   neuroephys study-add D:\Study01 D:\Projects\S01\neuroflow_project.json --animal A01 --session S01
   neuroephys study-inspect D:\Study01
   neuroephys study-run D:\Study01 --model "Linear SVM" --group-by animal --conditions correct error

English SVG/PNG figures, trial features, held-out metrics, predictions, session summaries,
and full JSON are written to ``results/multi_session`` inside the Study.

.. raw:: html

   <img class="product-shot" src="../assets/neuroephys-decoding-en.png"
        alt="NeuroEphys AI cross-validation, permutation, and ROC panels">

The lower row keeps time-resolved performance, population trajectories, and
unit feature importance visible as separate editable panels.

.. raw:: html

   <img class="product-shot" src="../assets/neuroephys-decoding-detail-en.png"
        alt="NeuroEphys AI time-resolved decoding and population detail">
