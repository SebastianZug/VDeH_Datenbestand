"""
VDEh Pipeline Runner
Führt die VDEh-Analyse-Pipeline in der korrekten Reihenfolge aus.
"""
import sys
from pathlib import Path

# Projektroot zum Python-Pfad hinzufügen
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pipelines.utils.notebook_executor import NotebookExecutor

# Pipeline-Definition
VDEH_NOTEBOOKS = [
    "notebooks/01_vdeh_preprocessing/01_vdeh_data_loading.ipynb",
    "notebooks/01_vdeh_preprocessing/02_vdeh_data_preprocessing.ipynb",
    "notebooks/01_vdeh_preprocessing/03_vdeh_language_detection.ipynb",
    "notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb",
    "notebooks/01_vdeh_preprocessing/05_vdeh_dnb_loc_fusion.ipynb"
]

def run_vdeh_pipeline():
    """Führt die VDEh-Analyse Pipeline aus."""
    executor = NotebookExecutor(
        pipeline_name="vdeh",
        notebooks=VDEH_NOTEBOOKS,
        kernel_name="bibo-analysis"
    )
    success = executor.run_pipeline()
    return 0 if success else 1

if __name__ == "__main__":
    exit(run_vdeh_pipeline())