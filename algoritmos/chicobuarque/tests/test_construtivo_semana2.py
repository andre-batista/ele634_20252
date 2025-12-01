# tests/test_construtivo_semana2.py
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "andre_repositorio"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from adapters.loader_andre import load_andre_instance
from core.instance import Instance
from core.solution import Solution
"""
Teste (Semana 2): construtivo simples iterando sobre alguns nós e aplicando
a melhor inserção na frota; checa Tmax, unicidade de visitas e limite r.
"""

def flatten(routes):
    return [trip for trips in routes.values() for trip in trips]

def main():
    # 1) Carrega instância pequena
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    # 2) Constrói solução incremental
    sol = Solution.new_empty(inst)

    # conjunto de nós a inserir (curto para teste rápido)
    nodes = list(range(1, min(inst.n, 6) + 1))  # 1..6 (ou até n)
    print("Nós a inserir:", nodes)

    for k in nodes:
        choice = sol.apply_best_insertion_across_fleet(k)
        print("Inseriu", k, "=>", choice)

    # 3) Impressão da solução
    print(sol.pretty())

    # 4) Sanity checks
    # 4.1 Tmax em todas as viagens
    for v in range(inst.K):
        for trip in sol.routes[v]:
            assert sol.trip_respects_Tmax(trip), f"Tmax violado no veículo {v}: {trip}"

    # 4.2 Cada nó inserido aparece exatamente uma vez
    all_trips = flatten(sol.routes)
    visits = []
    for trip in all_trips:
        visits.extend([x for x in trip if x != 0])
    for k in nodes:
        assert visits.count(k) == 1, f"Nó {k} não foi inserido exatamente uma vez."

    # 4.3 Limite de viagens por veículo
    for v in range(inst.K):
        assert len(sol.routes[v]) <= inst.r, f"Veículo {v} excedeu r={inst.r} viagens"

    print("[OK] Construtivo simples finalizado com sucesso.")

if __name__ == "__main__":
    main()
