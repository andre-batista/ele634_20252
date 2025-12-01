# tests/test_resumo_semana1.py
from pathlib import Path
import sys
import math
"""
Teste (Semana 1): imprime/resume estatísticas (shape/min/max) das matrizes
para pequena.json e media.json.
"""

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
ANDRE = ROOT / "andre_repositorio"
if str(ANDRE) not in sys.path:
    sys.path.insert(0, str(ANDRE))

def _minmax(M):
    m = math.inf
    Mx = -math.inf
    # Funciona com lista de listas ou numpy.ndarray 2D
    for row in M:
        for v in row:
            if v < m: m = v
            if v > Mx: Mx = v
    return m, Mx

def _shape(M):
    # Evita "if M" (ambíguo no numpy)
    try:
        r = len(M)
        c = len(M[0])
        return (r, c)
    except Exception:
        return (None, None)

def resumo(json_path: Path):
    from dados import carrega_dados_json
    d = carrega_dados_json(str(json_path))

    n   = d.n
    K   = d.K
    r   = d.r
    Tmax= getattr(d, "Tmax", getattr(d, "tempoMaximo", None))
    D,T,c = d.D, d.T, d.c
    s   = d.s
    e   = getattr(d, "inicioJanela", None)
    l   = getattr(d, "fimJanela", None)

    Dmin, Dmax = _minmax(D)
    Tmin, TmaxM = _minmax(T)
    cmin, cmax = _minmax(c)

    print(f"=== {json_path.name} ===")
    print(f"n={n} | K={K} | r={r} | Tmax={Tmax}")
    print(f"D: shape={_shape(D)}, min={Dmin:.2f}, max={Dmax:.2f}")
    print(f"T: shape={_shape(T)}, min={Tmin:.2f}, max={TmaxM:.2f}")
    print(f"c: shape={_shape(c)}, min={cmin:.2f}, max={cmax:.2f}")

    media_s = sum(s)/len(s)
    print(f"s: len={len(s)}, média={media_s:.2f}, min={min(s):.2f}, max={max(s):.2f}")

    if e is None or l is None:
        print("janelas: não definidas (e/l = None)")
    else:
        e_ex = e[1:4] if len(e) > 3 else e
        l_ex = l[1:4] if len(l) > 3 else l
        print(f"janelas: len(e)={len(e)}, len(l)={len(l)}, exemplo e[1..3]={e_ex}, l[1..3]={l_ex}")
    print()

def main():
    base = ROOT / "andre_repositorio" / "dados"
    for nome in ("pequena.json", "media.json"):
        p = base / nome
        if p.exists():
            resumo(p)
        else:
            print(f"[WARN] não encontrado: {p}")

if __name__ == "__main__":
    main()
