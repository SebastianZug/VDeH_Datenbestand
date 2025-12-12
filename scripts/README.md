# Scripts Directory

This directory contains utility scripts for the VDEH bibliographic data analysis project.

## Archive

- **`archive_old_tests/`**: Historical test and development scripts from the project development phase. Kept for reference but not needed for normal operation.

## Usage

All main functionality is now integrated into the Jupyter notebooks in `notebooks/`. The scripts in this directory were used during development and testing.

For running the main pipeline, use the notebooks:

```bash
# Run full pipeline
poetry run papermill notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb output_04.ipynb
poetry run papermill notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb output_05.ipynb
poetry run papermill notebooks/02_vdeh_analysis/01_project_report_generator.ipynb output_report.ipynb
```
