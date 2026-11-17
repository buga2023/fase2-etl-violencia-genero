"""
Monta o painel final da Fase 3 em um unico arquivo HTML, com os dados embutidos,
para abrir em qualquer navegador sem servidor e sem internet.
Passos: roda gerar_dados.py, injeta dados.js no template no lugar de /*__DADOS__*/.
"""
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SAIDA = "painel_feminicidio_fase3.html"

subprocess.run([sys.executable, str(AQUI / "gerar_dados.py")], check=True)

template = (AQUI / "painel_template.html").read_text(encoding="utf-8")
dados = (AQUI / "dados.js").read_text(encoding="utf-8")
html = template.replace("/*__DADOS__*/", dados)
(AQUI / SAIDA).write_text(html, encoding="utf-8")
print(f"{SAIDA}: {len(html):,} bytes")
