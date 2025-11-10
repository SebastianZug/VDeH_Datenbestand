"""
Gemeinsame Funktionalität für die Ausführung von Jupyter Notebooks in Pipelines.
"""
import papermill as pm
from pathlib import Path
import datetime
import sys

class NotebookExecutor:
    def __init__(self, pipeline_name: str, notebooks: list, kernel_name: str = None):
        self.pipeline_name = pipeline_name
        self.notebooks = notebooks
        self.kernel_name = kernel_name or "python3"
        self.output_dir = Path("logs/pipeline_runs") / pipeline_name
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_pipeline(self, parameters: dict = None):
        """Führt die Pipeline-Notebooks sequentiell aus."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n🚀 Starte {self.pipeline_name} Pipeline Run: {run_dir}\n")
        
        for i, nb_path in enumerate(self.notebooks, 1):
            nb_name = Path(nb_path).stem
            output_nb = run_dir / f"{i:02d}_{nb_name}_executed.ipynb"
            
            print(f"[{i}/{len(self.notebooks)}] Executing: {nb_path} ...")
            try:
                pm.execute_notebook(
                    input_path=nb_path,
                    output_path=output_nb,
                    parameters=parameters or {},
                    kernel_name=self.kernel_name,
                    log_output=True
                )
                print(f"   ✅ Erfolgreich: {output_nb}")
            except Exception as e:
                print(f"   ❌ Fehler in {nb_path}: {e}")
                print("   Pipeline abgebrochen.")
                return False
                
        print(f"\n🎉 Pipeline abgeschlossen! Alle Notebooks ausgeführt.\nErgebnisse: {run_dir}\n")
        return True