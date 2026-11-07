# Regenera las imágenes del MER y del DW desde los bloques mermaid de los .md.
# Requiere: npm install -g @mermaid-js/mermaid-cli
# Uso (desde la carpeta del proyecto): powershell -File bd\img\generar_imagenes.ps1
python -c "import re;[open(o,'w',encoding='utf-8').write(re.search(r'```mermaid\n(.*?)```',open(f,encoding='utf-8').read(),re.S).group(1)) for f,o in [('bd/MER_SIPA.md','bd/img/MER_SIPA.mmd'),('bd/DW_SIPA.md','bd/img/DW_SIPA.mmd')]]"
mmdc -i bd/img/MER_SIPA.mmd -o bd/img/MER_SIPA.png -s 3 -b white
mmdc -i bd/img/DW_SIPA.mmd  -o bd/img/DW_SIPA.png  -s 3 -b white
