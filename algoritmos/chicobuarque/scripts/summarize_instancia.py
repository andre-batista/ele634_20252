#!/usr/bin/env python
import sys
from pathlib import Path

"""
Script: summarize_instancia
---------------------------
Entrada: caminho para o JSON do André.
Ação: carrega e imprime estatísticas resumidas:
- dimensões de D/T/c
- min/max
- presença de janelas (e/l)

Uso:
    python scripts/summarize_instancia.py andre_repositorio/dados/pequena.json
"""

ROOT = Path(__file__).resolve().parents[1]
ANDRE = ROOT / "andre_repositorio"
SRC = ROOT / "src"
for p in (ANDRE, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from adapters.loader_andre import load_andre_instance
from core.instance import Instance

def _minmax(M):
    vals = [v for row in M for v in row]
    return min(vals), max(vals)

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/summarize_instancia.py <json>")
        sys.exit(1)
    p = Path(sys.argv[1]).resolve()
    raw = load_andre_instance(str(p))
    inst = Instance.from_andre(raw)
    Dmin, Dmax = _minmax(inst.D)
    Tmin, Tmax = _minmax(inst.T)
    cmin, cmax = _minmax(inst.c)
    print(f"n={inst.n} | K={inst.K} | r={inst.r} | Tmax={inst.Tmax}")
    print(f"D: {len(inst.D)}x{len(inst.D[0])}, min={Dmin:.2f}, max={Dmax:.2f}")
    print(f"T: {len(inst.T)}x{len(inst.T[0])}, min={Tmin:.2f}, max={Tmax:.2f}")
    print(f"c: {len(inst.c)}x{len(inst.c[0])}, min={cmin:.2f}, max={cmax:.2f}")
    has_windows = inst.e is not None and inst.l is not None
    print("janelas:", "definidas" if has_windows else "não definidas")

if __name__ == "__main__":
    main()
