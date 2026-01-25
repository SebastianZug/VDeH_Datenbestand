--[[
Pandoc Lua Filter für Mermaid-Diagramme
Konvertiert Mermaid-Codeblöcke in Bilder mittels mmdc (Mermaid CLI)

Autor: Claude
Datum: 2026-01-02
--]]

local system = require 'pandoc.system'

-- Konfiguration
local mermaid_counter = 0
local output_dir = "paper/figures/mermaid"
local mmdc_path = "/home/sz/.nvm/versions/node/v20.18.0/bin/mmdc"

-- Hilfsfunktion: Erstellt Output-Verzeichnis
local function ensure_output_dir()
  os.execute("mkdir -p " .. output_dir)
end

-- Hilfsfunktion: Generiert eindeutigen Dateinamen
local function get_output_filename()
  mermaid_counter = mermaid_counter + 1
  return output_dir .. "/diagram_" .. mermaid_counter .. ".png"
end

-- Hilfsfunktion: Schreibt Mermaid-Code in temporäre Datei
local function write_temp_file(content)
  local temp_file = os.tmpname() .. ".mmd"
  local file = io.open(temp_file, "w")
  file:write(content)
  file:close()
  return temp_file
end

-- Hilfsfunktion: Konvertiert Mermaid zu PNG
local function mermaid_to_png(mermaid_code, output_file)
  local temp_file = write_temp_file(mermaid_code)

  -- mmdc Befehl mit höherer Auflösung und fester Breite für PDF
  -- -w 1200: Breite in Pixeln (für gute Qualität in PDF)
  -- -s 2: Scale-Faktor für höhere Auflösung
  -- -b transparent: Transparenter Hintergrund
  local cmd = string.format(
    '%s -i "%s" -o "%s" -b transparent -w 1200 -s 2',
    mmdc_path,
    temp_file,
    output_file
  )

  -- Führe mmdc aus
  local success = os.execute(cmd)

  -- Lösche temporäre Datei
  os.remove(temp_file)

  return success == 0 or success == true
end

-- Hauptfunktion: Verarbeitet CodeBlocks
function CodeBlock(elem)
  -- Prüfe, ob es ein Mermaid-Block ist
  if elem.classes[1] == "mermaid" then
    ensure_output_dir()

    local output_file = get_output_filename()
    local mermaid_code = elem.text

    -- Konvertiere zu PNG
    local success = mermaid_to_png(mermaid_code, output_file)

    if success then
      -- Erstelle Pandoc Image-Element
      -- Für LaTeX: width und height für proportionale Skalierung
      local img = pandoc.Image({}, output_file, "")
      img.attributes.width = "80%"
      img.attributes.height = "80%"

      -- Wrap in Figure mit optionaler Caption
      return pandoc.Para({img})
    else
      -- Fehlerfall: Gebe Original-Codeblock zurück mit Warnung
      io.stderr:write("WARNUNG: Mermaid-Konvertierung fehlgeschlagen für Diagramm " .. mermaid_counter .. "\n")
      return elem
    end
  end

  return nil
end

-- Rückgabe der Filter-Funktionen
return {
  {CodeBlock = CodeBlock}
}
