"""
SIPA · Símbolos seguros en los documentos Word.

Algunos programas (Word sin la fuente Cambria Math, visores de celular, Google
Docs) sustituyen la fuente por Arial o Calibri, que no tienen ciertos símbolos
Unicode y los muestran como cuadritos. Este módulo revisa un .docx ya guardado y:

  - cambia las flechas largas por → (que sí existe en Arial y Calibri);
  - convierte los subíndices y superíndices Unicode (₀ ₁ ₖ ᵢ ᵀ ᶜ …) en texto
    normal con formato de subíndice o superíndice de Word.

Uso desde un generador, después de doc.save(ruta):
    from simbolos_seguros import asegurar
    asegurar(ruta)
O desde la terminal, sobre archivos ya hechos:
    python scripts/simbolos_seguros.py documento1.docx documento2.docx
"""
import copy
import sys

from docx import Document
from docx.text.run import Run

REEMPLAZO = {"⟹": "→", "⇒": "→", "⟶": "→", "▸": "→", "✓": "(sí)"}
SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₔₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ", "0123456789+-=()aeoxəhklmnpstijruv"))
SUP = {"ᵀ": "T", "ᶜ": "c", "ᵏ": "k", "ⁿ": "n", "ⁱ": "i"}


def _tramos(texto):
    """Parte el texto en (fragmento, 'normal'|'sub'|'sup')."""
    out = []
    for ch in texto:
        ch = REEMPLAZO.get(ch, ch)
        tipo, c = ("sub", SUB[ch]) if ch in SUB else (("sup", SUP[ch]) if ch in SUP else ("normal", ch))
        if out and out[-1][1] == tipo:
            out[-1][0] += c
        else:
            out.append([c, tipo])
    return out


def _arreglar_parrafo(p):
    for run in list(p.runs):
        t = run.text
        if not any(c in REEMPLAZO or c in SUB or c in SUP for c in t):
            continue
        tramos = _tramos(t)
        base = run._r
        original = copy.deepcopy(base)      # formato del run antes de tocarlo
        anterior = base
        for i, (frag, tipo) in enumerate(tramos):
            if i == 0:
                r = run
            else:
                nuevo = copy.deepcopy(original)
                anterior.addnext(nuevo)
                anterior = nuevo
                r = Run(nuevo, p)
            r.text = frag
            if tipo == "sub":
                r.font.subscript = True
            elif tipo == "sup":
                r.font.superscript = True


def _parrafos(doc):
    yield from doc.paragraphs
    for t in doc.tables:
        for fila in t.rows:
            for celda in fila.cells:
                yield from celda.paragraphs
    for s in doc.sections:
        for parte in (s.header, s.footer):
            yield from parte.paragraphs


def asegurar(ruta):
    doc = Document(ruta)
    for p in _parrafos(doc):
        _arreglar_parrafo(p)
    doc.save(ruta)


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        asegurar(ruta)
        print("listo:", ruta)
