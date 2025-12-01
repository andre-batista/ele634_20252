#!/usr/bin/env python
import sys
from pathlib import Path

"""
Script: check_instancia
-----------------------
Entrada: caminho para o JSON do André.
Ação: carrega a instância, valida campos básicos e imprime um resumo (n, K, r, Tmax).
Uso rápido:
    python scripts/check_instancia.py andre_repositorio/dados/pequena.json
"""

ROOT = Path(__file__).resolve().parents[1]
ANDRE = ROOT / "andre_repositorio"
SRC = ROOT / "src"
for p in (ANDRE, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from adapters.loader_andre import load_andre_instance
from core.instance import Instance

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/check_instancia.py <caminho_para_json>")
        sys.exit(1)
    p = Path(sys.argv[1]).resolve()
    raw = load_andre_instance(str(p))
    inst = Instance.from_andre(raw)

    n1 = inst.n + 1
    for name, M in [("D", inst.D), ("T", inst.T), ("c", inst.c)]:
        assert len(M) == n1 and all(len(r) == n1 for r in M), f"{name} deve ser {n1}x{n1}"
        assert all(M[i][i] == 0 for i in range(n1)), f"{name} diagonal deve ser 0"
        assert all(v >= 0 for r in M for v in r), f"{name} com valores negativos"
    assert len(inst.s) == n1, "s deve ter n+1"
    print(f"[OK] {p.name}: n={inst.n}, K={inst.K}, r={inst.r}, Tmax={inst.Tmax}")

if __name__ == "__main__":
    main()
