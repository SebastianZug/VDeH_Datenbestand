# Bibliographic Data Analysis Project

Multi-source bibliographic data analysis comparing VDEH (Verein Deutscher Bibliothekare) acquisitions with UB TUBAF (University Library TU Bergakademie Freiberg) collections.

## 🎯 Project Overview

This project analyzes and compares bibliographic data from two sources:
- **VDEH**: OAI-PMH XML format (~58,760 records)
- **UB TUBAF**: MAB2 format bibliographic data

### Key Features
- ✅ XML/MAB2 parsing and data extraction
- ✅ Professional language detection with `langdetect`
- ✅ Data quality analysis and missing values visualization
- ✅ Memory-optimized data processing
- ✅ Comprehensive export capabilities (Parquet, CSV)
- ✅ Configurable analysis pipeline

## 🏗️ Project Structure

```
├── notebooks/                          # Jupyter analysis notebooks
│   ├── 01_individual_analysis/         # Single-source analyses
│   │   ├── vdeh_analysis.ipynb        # VDEH data analysis
│   │   └── tubaf_analysis.ipynb       # UB TUBAF analysis
│   └── 02_comparative_analysis/        # Cross-source comparisons
├── src/                                # Source code
│   ├── parsers/                       # Data parsers
│   │   ├── vdeh_parser.py            # OAI-PMH XML parser
│   │   └── mab2_parser.py            # MAB2 format parser
│   └── config_loader.py              # Configuration management
├── config.yaml                        # Main configuration file
├── Pipfile                           # Python dependencies
└── README.md                         # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pipenv

### Installation
```bash
# Clone the repository
git clone https://github.com/SebastianZug/bibo-analysis.git
cd bibo-analysis

# Install dependencies
pipenv install

# Activate virtual environment
pipenv shell
```

### Configuration
1. Copy your data files to the appropriate directories (see `config.yaml`)
2. Adjust configuration in `config.yaml` if needed
3. Run the analysis notebooks

### Basic Usage
```bash
# Start Jupyter Lab
jupyter lab

# Or run individual notebooks
jupyter nbconvert --execute notebooks/01_individual_analysis/vdeh_analysis.ipynb
```

## 📊 Data Sources

### VDEH Data
- **Format**: OAI-PMH XML with MAB fields
- **Content**: Library acquisitions from VDEH member libraries
- **Size**: ~58,760 bibliographic records
- **Fields**: Title, Authors, Publication Year, Language

### UB TUBAF Data  
- **Format**: MAB2 (Maschinelles Austauschformat für Bibliotheken)
- **Content**: University library catalog data
- **Fields**: Comprehensive bibliographic metadata

## 🔧 Configuration

The project uses a centralized YAML configuration system:

```yaml
# Example configuration structure
data_sources:
  vdeh:
    path: "data/vdeh/raw/VDEH_mab_all.xml"
    encoding: "utf-8"
    estimated_records: 58760
  
data_processing:
  language_detection:
    min_text_length: 10
    confidence_threshold: 0.5
```

## 📈 Analysis Features

### Data Quality Analysis
- Missing values patterns and correlations
- Completeness scoring per record
- Field-specific quality metrics

### Language Detection
- Automatic language identification using `langdetect`
- Confidence scoring and filtering
- Support for multiple languages

### Visualization
- Missing values heatmaps
- Language distribution charts  
- Temporal analysis of data quality
- Export-ready publication graphics

### Export Capabilities
- **Parquet**: High-performance columnar format
- **CSV**: Excel-compatible summaries
- **JSON**: Metadata and analysis results

## 🛠️ Development

### Code Structure
- **Modular Design**: Separate parsers for different data formats
- **Configuration-Driven**: All parameters externalized to YAML
- **Memory Optimized**: Efficient handling of large datasets
- **Notebook-Based**: Interactive analysis and visualization

### Adding New Data Sources
1. Create parser in `src/parsers/`
2. Add configuration section to `config.yaml`
3. Create analysis notebook in appropriate directory

## 📋 Requirements

### Core Dependencies
- pandas >= 1.5.0
- matplotlib >= 3.6.0
- seaborn >= 0.12.0
- langdetect >= 1.0.9
- lxml >= 4.9.0
- pyarrow >= 10.0.0 (for Parquet support)
- tqdm >= 4.64.0 (progress bars)

### Development Dependencies
- jupyter >= 1.0.0
- papermill >= 2.4.0 (notebook automation)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- [VDEH](https://www.vdeh.de/) - Verein Deutscher Bibliothekare
- [TU Bergakademie Freiberg](https://tu-freiberg.de/) - University Library

## 📞 Contact

**Sebastian Zug** - [@SebastianZug](https://github.com/SebastianZug)

Project Link: [https://github.com/SebastianZug/bibo-analysis](https://github.com/SebastianZug/bibo-analysis)

---

**Note**: This repository contains code and configuration only. Data files are excluded for privacy and size reasons.