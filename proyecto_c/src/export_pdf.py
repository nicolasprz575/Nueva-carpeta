"""
Script auxiliar para exportar el informe Markdown a PDF
Requiere: pip install markdown2 weasyprint

Alternativas si WeasyPrint no funciona:
1. Usar pandoc: pandoc informe_caso1.md -o informe_caso1.pdf
2. Usar VS Code: Extensión "Markdown PDF"
3. Usar servicio web: https://www.markdowntopdf.com/
"""

import os
from pathlib import Path

def export_markdown_to_pdf():
    """Exporta el informe Markdown a PDF usando diferentes métodos"""
    
    # Rutas
    proyecto_root = Path(__file__).parent.parent
    md_file = proyecto_root / "docs" / "informe_caso1.md"
    pdf_file = proyecto_root / "docs" / "informe_caso1.pdf"
    
    print(f"Archivo Markdown: {md_file}")
    print(f"Archivo PDF destino: {pdf_file}")
    
    if not md_file.exists():
        print(f"❌ ERROR: No se encuentra el archivo {md_file}")
        return
    
    print("\n" + "="*70)
    print("OPCIONES PARA EXPORTAR A PDF")
    print("="*70)
    
    print("\n1️⃣ OPCIÓN 1: Usar VS Code (Recomendado)")
    print("   - Instalar extensión: 'Markdown PDF' (yzane.markdown-pdf)")
    print("   - Abrir informe_caso1.md en VS Code")
    print("   - Click derecho → 'Markdown PDF: Export (pdf)'")
    
    print("\n2️⃣ OPCIÓN 2: Usar Pandoc (línea de comandos)")
    print("   - Instalar Pandoc: https://pandoc.org/installing.html")
    print("   - Ejecutar comando:")
    print(f'     pandoc "{md_file}" -o "{pdf_file}" --pdf-engine=xelatex')
    
    print("\n3️⃣ OPCIÓN 3: Usar servicio web")
    print("   - Visitar: https://www.markdowntopdf.com/")
    print("   - Subir el archivo informe_caso1.md")
    print("   - Descargar el PDF generado")
    
    print("\n4️⃣ OPCIÓN 4: Usar Python con WeasyPrint")
    print("   - Instalar: pip install markdown2 weasyprint")
    print("   - Descomentar el código al final de este script")
    
    print("\n" + "="*70)
    print(f"✅ El archivo Markdown está listo en: {md_file}")
    print("   Elige cualquiera de las opciones anteriores para exportar a PDF")
    print("="*70 + "\n")

# OPCIÓN 4: Código para usar WeasyPrint (descomentar si tienes instalado)
"""
def export_with_weasyprint():
    try:
        import markdown2
        from weasyprint import HTML, CSS
        
        proyecto_root = Path(__file__).parent.parent
        md_file = proyecto_root / "docs" / "informe_caso1.md"
        pdf_file = proyecto_root / "docs" / "informe_caso1.pdf"
        
        # Leer Markdown
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convertir a HTML
        html_content = markdown2.markdown(md_content, extras=['tables', 'fenced-code-blocks'])
        
        # CSS básico para el PDF
        css = CSS(string='''
            @page { size: A4; margin: 2cm; }
            body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.6; }
            h1 { font-size: 24pt; color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            h2 { font-size: 18pt; color: #34495e; margin-top: 20px; border-bottom: 2px solid #95a5a6; }
            h3 { font-size: 14pt; color: #7f8c8d; }
            table { border-collapse: collapse; width: 100%; margin: 15px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #3498db; color: white; }
            code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
            pre { background-color: #f8f8f8; padding: 10px; border-left: 3px solid #3498db; overflow-x: auto; }
        ''')
        
        # Generar PDF
        HTML(string=html_content).write_pdf(pdf_file, stylesheets=[css])
        
        print(f"✅ PDF generado exitosamente: {pdf_file}")
        
    except ImportError:
        print("❌ ERROR: Falta instalar módulos")
        print("   Ejecutar: pip install markdown2 weasyprint")
    except Exception as e:
        print(f"❌ ERROR al generar PDF: {e}")
"""

if __name__ == "__main__":
    export_markdown_to_pdf()
    
    # Descomentar la siguiente línea si tienes WeasyPrint instalado:
    # export_with_weasyprint()
