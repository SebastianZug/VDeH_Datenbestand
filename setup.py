#!/usr/bin/env python3
"""
Setup-Skript für die Bibo-Analysis Umgebung.
Installiert alle Abhängigkeiten und richtet Jupyter Kernels ein.
"""
import json
import subprocess
from pathlib import Path

def setup_project():
    """Richtet das Projekt mit allen Abhängigkeiten ein."""
    print("🚀 Starte Projekt-Setup...")
    
    # Poetry Installation prüfen
    try:
        subprocess.run(["poetry", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Poetry nicht gefunden. Bitte installieren Sie Poetry: https://python-poetry.org/docs/#installation")
        return False
    
    # Virtuelle Umgebung erstellen und Abhängigkeiten installieren
    print("\n📦 Installiere Projekt-Abhängigkeiten...")
    subprocess.run(["poetry", "install"], check=True)
    
    # Kernel-Konfiguration erstellen
    print("\n🔧 Konfiguriere Jupyter Kernel...")
    kernel_name = "bibo-analysis"
    kernel_json = {
        "argv": ["poetry", "run", "python", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Bibo Analysis (Poetry)",
        "language": "python",
        "metadata": {
            "debugger": True
        }
    }
    
    # Kernel installieren
    kernels_dir = Path.home() / ".local/share/jupyter/kernels" / kernel_name
    kernels_dir.mkdir(parents=True, exist_ok=True)
    
    with open(kernels_dir / "kernel.json", "w") as f:
        json.dump(kernel_json, f, indent=2)
    
    print(f"\n✅ Jupyter Kernel '{kernel_name}' installiert!")
    print("\n🎉 Setup abgeschlossen! Sie können nun die Notebooks mit dem 'Bibo Analysis' Kernel ausführen.")
    
    # Erstelle Notebook-Config
    create_notebook_config()
    return True

def create_notebook_config():
    """Erstellt eine einheitliche Notebook-Konfiguration."""
    config = {
        "kernel_name": "bibo-analysis",
        "language_info": {
            "name": "python",
            "version": "3.9"
        }
    }
    
    config_dir = Path("notebooks") / ".jupyter"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    with open(config_dir / "notebook_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("\n📝 Notebook-Konfiguration erstellt")

if __name__ == "__main__":
    setup_project()