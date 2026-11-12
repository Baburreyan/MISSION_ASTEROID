"""Build and optionally execute the official Project Sentinel capstone notebook.

The notebook intentionally imports the versioned pipeline rather than duplicating
training logic. This keeps the submission executable in sequence while leaving an
auditable Python source of truth for the staged candidate.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "hazardous_asteroid_prediction_final.ipynb"


def markdown(source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in source.splitlines()]}


def code(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.splitlines()],
    }


def cells() -> list[dict[str, Any]]:
    return [
        markdown(
            "# Project Sentinel — Canonical Three-Feature Reproducibility Benchmark\n\n"
            "This is the official capstone notebook. It creates a separate staged candidate and **does not** replace "
            "the active legacy deployment artifact (`v1.0.0`). The task is historical hazardous-label classification, "
            "not collision or impact prediction."
        ),
        markdown(
            "## Reproducibility contract\n\n"
            "Run from the repository root after installing `sentinel_training/requirements-canonical.txt`. "
            "The dataset path is portable: it first resolves the provided Downloads CSV relative to this project. "
            "All generated files are deterministic and are written only beneath `sentinel_training/`."
        ),
        code(
            "from pathlib import Path\n"
            "import json\n"
            "import joblib\n"
            "import numpy as np\n"
            "import pandas as pd\n\n"
            "from sentinel_training.canonical_pipeline import (\n"
            "    DEFAULT_DATASET_PATH, DEFAULT_LEGACY_METADATA_PATH, DEFAULT_LEGACY_MODEL_PATH,\n"
            "    FEATURES, MODEL_PARAMETERS, SEEDS, STAGING_DIR, dataset_provenance, feature_schema, sha256_file,\n"
            "    legacy_preservation_manifest, load_config, load_dataset, create_group_splits,\n"
            "    evaluate,\n"
            ")\n\n"
            "config = load_config()\n"
            "DATASET_PATH = DEFAULT_DATASET_PATH\n"
            "print(f'Dataset: {DATASET_PATH}')\n"
            "print('Canonical model inputs:', FEATURES)\n"
            "print('Pinned model parameters:', MODEL_PARAMETERS)"
        ),
        markdown(
            "# Phase 1 — Data preprocessing, validation, and provenance\n\n"
            "The supplied CSV is treated as the canonical project copy, but its source URL/release, field dictionary, "
            "and hazardous-label definition were not supplied. Units are therefore deployment-declared rather than "
            "source-verified. Names and identifiers are excluded from predictors."
        ),
        code(
            "frame = load_dataset(DATASET_PATH)\n"
            "dataset_info = dataset_provenance(frame, DATASET_PATH)\n"
            "legacy_info = legacy_preservation_manifest(DEFAULT_LEGACY_MODEL_PATH, DEFAULT_LEGACY_METADATA_PATH)\n"
            "print(json.dumps({\n"
            "    'shape': [dataset_info['rows'], len(dataset_info['columns'])],\n"
            "    'columns': dataset_info['columns'],\n"
            "    'dtypes': dataset_info['dtypes'],\n"
            "    'missing_values': dataset_info['missing_values'],\n"
            "    'duplicate_rows': dataset_info['exact_duplicate_rows'],\n"
            "    'constant_columns': dataset_info['constant_columns'],\n"
            "    'nonfinite_numeric_values': dataset_info['nonfinite_numeric_values'],\n"
            "    'unique_asteroid_ids': dataset_info['unique_asteroid_ids'],\n"
            "    'target_distribution': dataset_info['target_distribution'],\n"
            "    'csv_sha256': dataset_info['sha256'],\n"
            "    'legacy_v1_0_0_model_sha256': legacy_info['model_sha256'],\n"
            "}, indent=2))"
        ),
        markdown(
            "# Phase 2 — Exploratory data analysis\n\n"
            "The tables below describe the provided observations only. They support data quality and model-design checks; "
            "they do not establish causal relationships. The `id`, `name`, `orbiting_body`, and `sentry_object` fields "
            "are not used as model inputs."
        ),
        code(
            "print('Class distribution by row:')\n"
            "print(frame['hazardous'].value_counts(dropna=False).rename_axis('hazardous').to_frame('rows'))\n"
            "print('\\nCanonical feature percentiles:')\n"
            "print(frame[list(FEATURES)].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).T)\n"
            "print('\\nFeature medians by historical label:')\n"
            "print(frame.groupby('hazardous')[list(FEATURES)].median())\n"
            "print('\\nFeature correlations:')\n"
            "print(frame[list(FEATURES)].corr())\n"
            "print('\\nFinding: these are associations in this historical labeled dataset, not physical or causal claims.')"
        ),
        markdown(
            "### Phase 2 figure and interpretation audit\n\n"
            "The capstone EDA still lacks rendered class-distribution, by-class feature-distribution, correlation-heatmap, "
            "diameter-versus-magnitude, and velocity-versus-miss-distance figures. The current pinned environment does not "
            "include Matplotlib or Seaborn, so this notebook records the dependency rather than fabricating figures. Once an "
            "approved plotting environment is available, add those figures using the already-validated `frame` and place a "
            "short descriptive finding directly below each figure."
        ),
        code(
            "import importlib.util\n"
            "plotting_audit = {name: importlib.util.find_spec(name) is not None for name in ('matplotlib', 'seaborn')}\n"
            "print(json.dumps({\n"
            "    'plotting_packages_available': plotting_audit,\n"
            "    'required_figures_not_yet_rendered': [\n"
            "        'hazardous-class distribution', 'feature distributions by class', 'correlation heatmap',\n"
            "        'diameter versus absolute magnitude', 'relative velocity versus miss distance'\n"
            "    ],\n"
            "    'interpretation_rule': 'Describe observed associations only; do not claim causation or physical impact risk.',\n"
            "}, indent=2))"
        ),
        markdown(
            "# Phase 3 — Feature engineering and schema\n\n"
            "The canonical candidate uses exactly three raw inputs in this order: `absolute_magnitude`, "
            "`relative_velocity`, and `miss_distance`. There is no imputation, scaling, resampling, or synthetic orbital "
            "data because these selected fields are complete and finite; the tree model is fitted on training data only. "
            "Diameter-derived and five-feature experiments are retained below as **experimental lineage only** and are not "
            "the deployed or staged canonical schema."
        ),
        code(
            "schema = feature_schema(frame)\n"
            "print(pd.DataFrame(schema).to_string(index=False))\n"
            "experimental_five_feature_lineage = [\n"
            "    'diameter_midpoint', 'diameter_range', 'relative_velocity', 'miss_distance', 'absolute_magnitude'\n"
            "]\n"
            "print('\\nExperimental five-feature lineage (not trained or exported by this canonical run):')\n"
            "print(experimental_five_feature_lineage)\n"
            "print('Diameter bounds are excluded here because the current deployment API accepts only the three canonical inputs.')"
        ),
        code(
            "diameter_columns = ['est_diameter_min', 'est_diameter_max']\n"
            "diameter_redundancy = frame[['absolute_magnitude', *diameter_columns]].copy()\n"
            "diameter_redundancy['log10_est_diameter_min'] = np.log10(diameter_redundancy['est_diameter_min'])\n"
            "diameter_redundancy['log10_est_diameter_max'] = np.log10(diameter_redundancy['est_diameter_max'])\n"
            "print('Diameter redundancy check (correlations):')\n"
            "print(diameter_redundancy.corr().loc[['absolute_magnitude'], ['log10_est_diameter_min', 'log10_est_diameter_max']])\n"
            "print('Finding: diameter-derived fields are assessed as redundant candidates, not added to the canonical three-feature deployment schema.')"
        ),
        markdown(
            "# Phase 4 — Group-aware model development and validation\n\n"
            "A two-stage, stratified split operates on unique asteroid IDs: 80/20 test by ID (seed 42), then 75/25 "
            "train/validation within the remaining IDs (seed 43). This prevents an asteroid from appearing in multiple "
            "partitions. Because earlier work may have examined observations in this CSV, the resulting test partition is a "
            "reproducibility benchmark—not a proven independent untouched holdout."
        ),
        code(
            "splits = create_group_splits(frame)\n"
            "print(json.dumps(splits.manifest, indent=2))"
        ),
        markdown(
            "## Phase 4 — Frozen candidate validation replication\n\n"
            "This notebook loads the existing staged `HistGradientBoostingClassifier` candidate without fitting or modifying it. "
            "Its recorded configuration is `learning_rate=0.03`, `max_iter=150`, `max_leaf_nodes=31`, `l2_regularization=5`, "
            "and `random_state=42`. The recorded threshold was selected from validation scores only by maximizing F2 subject "
            "to hazardous-class recall ≥ 0.95; no test score is used here for model or threshold selection."
        ),
        code(
            "STAGED_CANDIDATE_PATH = STAGING_DIR / 'sentinel_model_candidate_v1_1_0.joblib'\n"
            "STAGED_METADATA_PATH = STAGING_DIR / 'sentinel_model_candidate_v1_1_0.metadata.json'\n"
            "staged_metadata = json.loads(STAGED_METADATA_PATH.read_text(encoding='utf-8'))\n"
            "expected_candidate_hash = staged_metadata['candidate_model_sha256']\n"
            "actual_candidate_hash = sha256_file(STAGED_CANDIDATE_PATH)\n"
            "if actual_candidate_hash != expected_candidate_hash:\n"
            "    raise RuntimeError('Refusing to explain a staged model whose SHA-256 does not match its metadata.')\n"
            "candidate = joblib.load(STAGED_CANDIDATE_PATH)\n"
            "if tuple(candidate.feature_names_in_) != FEATURES:\n"
            "    raise AssertionError('Frozen candidate feature schema does not match the canonical three-feature contract.')\n"
            "if {name: candidate.get_params()[name] for name in MODEL_PARAMETERS} != MODEL_PARAMETERS:\n"
            "    raise AssertionError('Frozen candidate parameters do not match the recorded canonical configuration.')\n"
            "X_validation = frame.loc[splits.validation_mask, list(FEATURES)]\n"
            "y_validation = frame.loc[splits.validation_mask, 'hazardous'].astype(int)\n"
            "validation_scores = candidate.predict_proba(X_validation)[:, 1]\n"
            "selected_threshold = float(staged_metadata['threshold'])\n"
            "threshold_details = staged_metadata['threshold_selection']\n"
            "validation_metrics = evaluate(y_validation, validation_scores, selected_threshold)\n"
            "if validation_metrics != staged_metadata['validation_metrics']:\n"
            "    raise AssertionError('Reloaded frozen candidate did not reproduce the recorded validation metrics.')\n"
            "print(json.dumps({\n"
            "    'staged_candidate_path': str(STAGED_CANDIDATE_PATH),\n"
            "    'staged_candidate_sha256': actual_candidate_hash,\n"
            "    'threshold': selected_threshold,\n"
            "    'threshold_selection': threshold_details,\n"
            "    'validation_metrics': validation_metrics,\n"
            "    'fitting_or_tuning_performed_in_this_notebook_run': False,\n"
            "}, indent=2))"
        ),
        code(
            "from sklearn.metrics import accuracy_score, classification_report\n"
            "validation_predictions = (validation_scores >= selected_threshold).astype(int)\n"
            "validation_diagnostics = {\n"
            "    'accuracy': float(accuracy_score(y_validation, validation_predictions)),\n"
            "    'classification_report': classification_report(\n"
            "        y_validation, validation_predictions, labels=[0, 1],\n"
            "        target_names=['non_hazardous', 'hazardous'], zero_division=0, output_dict=True,\n"
            "    ),\n"
            "}\n"
            "print(json.dumps(validation_diagnostics, indent=2))\n"
            "print('These are validation diagnostics only. The reserved test partition remains unscored.')"
        ),
        markdown(
            "### Phase 4 comparison audit\n\n"
            "The canonical benchmark contains one frozen HistGradientBoostingClassifier candidate. A DummyClassifier, Logistic "
            "Regression, and Random Forest comparison has not been rerun on these exact manifests, so this notebook does not "
            "present legacy experiment outputs as comparable canonical results. Add the baseline comparison in a future, "
            "training-only extension before selecting a replacement model; do not use the reserved test partition for this work."
        ),
        code(
            "comparison_audit = {\n"
            "    'canonical_candidate': 'HistGradientBoostingClassifier v1.1.0-reproducibility-benchmark',\n"
            "    'canonical_baselines_rerun_on_saved_manifests': False,\n"
            "    'historical_experiment_metrics_reused_as_canonical': False,\n"
            "    'test_partition_used_for_selection': False,\n"
            "}\n"
            "print(json.dumps(comparison_audit, indent=2))"
        ),
        markdown(
            "# Phase 5 — Explainable AI and validation error analysis\n\n"
            "All results in this phase use only the **frozen staged candidate** and the saved validation partition. They do not "
            "fit, tune, or alter the model; they do not access the reserved test partition. Permutation importance measures the "
            "drop in validation average precision after a feature is shuffled. SHAP contributions explain this model's positive-class "
            "raw model output associated with the supplied historical label. Neither result establishes a causal astronomical mechanism, nor is the score a "
            "calibrated probability of an Earth impact."
        ),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import shap\n"
            "from sklearn.inspection import permutation_importance\n\n"
            "PHASE5_SEED = 42\n"
            "SHAP_SAMPLE_SIZE = 300\n"
            "permutation_result = permutation_importance(\n"
            "    candidate, X_validation, y_validation, scoring='average_precision',\n"
            "    n_repeats=10, random_state=PHASE5_SEED, n_jobs=1,\n"
            ")\n"
            "permutation_importance_table = pd.DataFrame({\n"
            "    'feature': list(FEATURES),\n"
            "    'mean_validation_pr_auc_decrease': permutation_result.importances_mean,\n"
            "    'std_validation_pr_auc_decrease': permutation_result.importances_std,\n"
            "}).sort_values('mean_validation_pr_auc_decrease', ascending=False, ignore_index=True)\n"
            "print('Permutation importance: validation average-precision decrease after shuffling (10 repeats).')\n"
            "print(permutation_importance_table.to_string(index=False))\n\n"
            "shap_indices = (\n"
            "    y_validation.groupby(y_validation).sample(\n"
            "        n=None, frac=SHAP_SAMPLE_SIZE / len(y_validation), random_state=PHASE5_SEED\n"
            "    ).index\n"
            ")\n"
            "# Deterministically top up only if rounding made the stratified sample smaller than 300.\n"
            "if len(shap_indices) < SHAP_SAMPLE_SIZE:\n"
            "    remaining = X_validation.index.difference(shap_indices)\n"
            "    top_up = pd.Series(remaining).sample(\n"
            "        n=SHAP_SAMPLE_SIZE - len(shap_indices), random_state=PHASE5_SEED\n"
            "    ).tolist()\n"
            "    shap_indices = shap_indices.append(pd.Index(top_up))\n"
            "X_shap = X_validation.loc[sorted(shap_indices), list(FEATURES)].copy()\n"
            "if len(X_shap) != SHAP_SAMPLE_SIZE:\n"
            "    raise AssertionError(f'Expected {SHAP_SAMPLE_SIZE} SHAP rows, found {len(X_shap)}.')\n"
            "tree_explainer = shap.TreeExplainer(candidate)\n"
            "shap_explanation = tree_explainer(X_shap)\n"
            "if shap_explanation.values.ndim == 3:\n"
            "    # Select the hazardous/positive output if this SHAP version returns an output dimension.\n"
            "    shap_explanation = shap.Explanation(\n"
            "        values=shap_explanation.values[:, :, 1],\n"
            "        base_values=np.asarray(shap_explanation.base_values)[:, 1],\n"
            "        data=shap_explanation.data, feature_names=list(FEATURES),\n"
            "    )\n"
            "if shap_explanation.values.shape != X_shap.shape:\n"
            "    raise AssertionError(f'Unexpected SHAP shape: {shap_explanation.values.shape}; expected {X_shap.shape}.')\n"
            "shap_additivity_max_abs_error = float(np.max(np.abs(\n"
            "    np.asarray(shap_explanation.base_values) + shap_explanation.values.sum(axis=1)\n"
            "    - candidate.decision_function(X_shap)\n"
            ")))\n"
            "if shap_additivity_max_abs_error > 1e-6:\n"
            "    raise AssertionError(f'SHAP additivity check failed: {shap_additivity_max_abs_error}.')\n"
            "mean_absolute_shap = pd.DataFrame({\n"
            "    'feature': list(FEATURES),\n"
            "    'mean_absolute_shap_value': np.abs(shap_explanation.values).mean(axis=0),\n"
            "}).sort_values('mean_absolute_shap_value', ascending=False, ignore_index=True)\n"
            "print(f'\\nSHAP uses a deterministic, label-stratified validation sample of {len(X_shap)} rows (seed={PHASE5_SEED}).')\n"
            "print('SHAP sample historical-label counts:', y_validation.loc[X_shap.index].value_counts().sort_index().to_dict())\n"
            "print('SHAP additivity max absolute error against decision_function:', shap_additivity_max_abs_error)\n"
            "print(mean_absolute_shap.to_string(index=False))\n\n"
            "plt.figure(figsize=(8, 4.8))\n"
            "shap.plots.beeswarm(shap_explanation, max_display=len(FEATURES), show=False)\n"
            "plt.title('Validation sample: global SHAP influence on model output')\n"
            "plt.tight_layout()"
        ),
        markdown(
            "### Phase 5 interpretation\n\n"
            "In this frozen validation run, `absolute_magnitude` ranked first by both the mean validation PR-AUC decrease and mean "
            "absolute SHAP value, followed by `miss_distance`, then `relative_velocity`. A larger positive permutation decrease means "
            "shuffling that input reduced validation PR-AUC more; a larger mean absolute SHAP value means the feature moved the model's "
            "raw decision output on the 300-row sample. These are model associations that can be correlated or conditional on other inputs—not causal "
            "astronomical findings, validation of unresolved source units, or a physical-risk explanation."
        ),
        code(
            "validation_predictions = (validation_scores >= selected_threshold).astype(int)\n"
            "validation_review = frame.loc[X_validation.index, ['id', 'name', *FEATURES, 'hazardous']].copy()\n"
            "validation_review['model_score'] = validation_scores\n"
            "validation_review['predicted_hazardous'] = validation_predictions.astype(bool)\n"
            "validation_review['prediction_margin'] = validation_review['model_score'] - selected_threshold\n\n"
            "true_positive = validation_review[(validation_review['hazardous']) & (validation_review['predicted_hazardous'])]\n"
            "true_negative = validation_review[(~validation_review['hazardous']) & (~validation_review['predicted_hazardous'])]\n"
            "if true_positive.empty or true_negative.empty:\n"
            "    raise RuntimeError('Validation partition lacks a true-positive or true-negative row for the requested SHAP waterfalls.')\n"
            "def median_score_index(records):\n"
            "    return (records['model_score'] - records['model_score'].median()).abs().sort_values(kind='mergesort').index[0]\n\n"
            "hazardous_index = median_score_index(true_positive)\n"
            "non_hazardous_index = median_score_index(true_negative)\n"
            "shap_single = tree_explainer(X_validation.loc[[hazardous_index, non_hazardous_index], list(FEATURES)])\n"
            "if shap_single.values.ndim == 3:\n"
            "    shap_single = shap.Explanation(\n"
            "        values=shap_single.values[:, :, 1],\n"
            "        base_values=np.asarray(shap_single.base_values)[:, 1],\n"
            "        data=shap_single.data, feature_names=list(FEATURES),\n"
            "    )\n"
            "for position, (label, row_index) in enumerate([\n"
            "    ('Representative true-positive historical hazardous label', hazardous_index),\n"
            "    ('Representative true-negative historical non-hazardous label', non_hazardous_index),\n"
            "]):\n"
            "    plt.figure(figsize=(8, 4.8))\n"
            "    shap.plots.waterfall(shap_single[position], max_display=len(FEATURES), show=False)\n"
            "    plt.title(label)\n"
            "    plt.tight_layout()\n\n"
            "false_positives = validation_review[(~validation_review['hazardous']) & (validation_review['predicted_hazardous'])].copy()\n"
            "false_negatives = validation_review[(validation_review['hazardous']) & (~validation_review['predicted_hazardous'])].copy()\n"
            "review_columns = ['id', 'name', *FEATURES, 'hazardous', 'model_score', 'prediction_margin']\n"
            "representative_false_positives = false_positives.assign(\n"
            "    distance_to_threshold=(false_positives['prediction_margin']).abs()\n"
            ").sort_values(['distance_to_threshold', 'id'], kind='mergesort').head(5)[review_columns]\n"
            "representative_false_negatives = false_negatives.assign(\n"
            "    distance_to_threshold=(false_negatives['prediction_margin']).abs()\n"
            ").sort_values(['distance_to_threshold', 'id'], kind='mergesort').head(5)[review_columns]\n"
            "print('Representative validation false positives: the five scores nearest the fixed threshold.')\n"
            "print(representative_false_positives.to_string(index=False))\n"
            "print('\\nRepresentative validation false negatives: the five scores nearest the fixed threshold.')\n"
            "print(representative_false_negatives.to_string(index=False))\n"
            "print('\\nSelection is deterministic and descriptive; it does not change the fixed threshold or model.')"
        ),
        markdown(
            "### Phase 5 limitations\n\n"
            "The selected waterfall rows are deterministic validation examples closest to their group’s median score, not case studies "
            "with external astronomical verification. The false-positive and false-negative tables are selected by distance to the existing "
            "threshold so they document boundary cases; they must not be generalized into a causal error mechanism. The model estimates "
            "the CSV’s historical label only, and dataset source provenance, label definition, and source-level unit verification remain unresolved."
        ),
        markdown(
            "# Phase 6 — Deployment preparation, staged export, and limitations\n\n"
            "This notebook only reads the existing staged candidate and its provenance. The legacy `sentinel_model.joblib` and its "
            "metadata are hash-audited and preserved byte-for-byte. The deterministic fixture had already verified the staged model "
            "reload at export time; no model, metadata, fixture, or report is written by this notebook. The test partition remains "
            "reserved and is intentionally unscored."
        ),
        code(
            "REFERENCE_FIXTURE_PATH = STAGING_DIR / 'reference_prediction_fixture.json'\n"
            "STAGING_REPORT_PATH = STAGING_DIR / 'canonical_training_report_v1_1_0.json'\n"
            "reference_fixture = json.loads(REFERENCE_FIXTURE_PATH.read_text(encoding='utf-8'))\n"
            "staging_report = json.loads(STAGING_REPORT_PATH.read_text(encoding='utf-8'))\n"
            "print(json.dumps({\n"
            "    'staged_model': str(STAGED_CANDIDATE_PATH),\n"
            "    'staged_metadata': str(STAGED_METADATA_PATH),\n"
            "    'reference_fixture': str(REFERENCE_FIXTURE_PATH),\n"
            "    'report': str(STAGING_REPORT_PATH),\n"
            "    'reload_check': staging_report['staged_model']['reloaded_predictions_identical'],\n"
            "    'test_partition_status': staging_report['test_partition_status'],\n"
            "    'notebook_run_wrote_model_or_staging_artifacts': False,\n"
            "}, indent=2))"
        ),
        markdown(
            "## Limitations and next decision\n\n"
            "- This model predicts the historical `hazardous` label in the supplied CSV. Its score is a model class score, "
            "not a calibrated physical impact probability.\n"
            "- Dataset source provenance, label definition, and source-verified units remain unresolved.\n"
            "- The candidate must receive a separately authorized, one-time final evaluation on the reserved benchmark test "
            "partition before any deployment decision.\n"
            "- Deployment is intentionally unchanged: the running API continues to use legacy v1.0.0."
        ),
    ]


def build() -> None:
    notebook = {
        "cells": cells(),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")


def execute() -> None:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    namespace: dict[str, Any] = {"__name__": "__notebook__"}
    for index, cell in enumerate(notebook["cells"], start=1):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        stdout = io.StringIO()
        try:
            # Preserve generated Phase 5 figures as standard notebook outputs so the
            # official submission remains one self-contained notebook.
            try:
                import matplotlib.pyplot as plt
                figures_before = set(plt.get_fignums())
            except ImportError:
                plt = None
                figures_before = set()
            with contextlib.redirect_stdout(stdout):
                exec(compile(source, f"notebook cell {index}", "exec"), namespace)
            output = stdout.getvalue()
            cell["execution_count"] = index
            outputs: list[dict[str, Any]] = []
            if output:
                outputs.append({"output_type": "stream", "name": "stdout", "text": output.splitlines(keepends=True)})
            if plt is not None:
                for figure_number in sorted(set(plt.get_fignums()) - figures_before):
                    figure = plt.figure(figure_number)
                    buffer = io.BytesIO()
                    figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
                    outputs.append({
                        "output_type": "display_data",
                        "data": {"image/png": base64.b64encode(buffer.getvalue()).decode("ascii")},
                        "metadata": {},
                    })
                    plt.close(figure)
            cell["outputs"] = outputs
        except Exception as exc:
            cell["execution_count"] = index
            cell["outputs"] = [{
                "output_type": "error", "ename": type(exc).__name__, "evalue": str(exc),
                "traceback": traceback.format_exc().splitlines(),
            }]
            NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(f"Notebook failed in cell {index}: {exc}") from exc
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Execute each code cell sequentially after building.")
    args = parser.parse_args()
    build()
    if args.execute:
        execute()
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
