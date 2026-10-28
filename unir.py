from pathlib import Path

IGNORAR = {"venv", ".venv", "__pycache__", ".git", "node_modules", "dist", "build"}
EXTENSIONES = {".py", ".toml", ".txt", ".md", ".json", ".yaml", ".yml", ".cfg", ".ini"}

with open("proyecto.txt", "w", encoding="utf-8") as salida:
    for ruta in sorted(Path(".").rglob("*")):
        if ruta.is_file() and ruta.suffix in EXTENSIONES \
           and not IGNORAR & set(ruta.parts) and ruta.name != "proyecto.txt":
            salida.write(f"\n\n===== {ruta} =====\n")
            salida.write(ruta.read_text(encoding="utf-8", errors="ignore"))