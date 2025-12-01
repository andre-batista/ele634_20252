# tests/test_best_insercao_frota_semana2.py
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
Teste (Semana 2): “melhor inserção na frota” (inserir em viagem corrente
ou abrir nova viagem 0->node->0 quando r permite). Checa Tmax e resultado.
"""

def flatten_routes(routes):
    """Lista plana com TODAS as viagens de TODOS os veículos."""
    return [trip for trips in routes.values() for trip in trips]

def main():
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    sol = Solution.new_empty(inst)

    # veículo 0 já tem 1 viagem: 0->1->0
    sol.start_new_trip(0)
    sol.add_stop_current_trip(0, 1)
    sol.finish_current_trip(0)

    # pede melhor opção pra inserir o nó 2 na frota
    choice = sol.apply_best_insertion_across_fleet(node=2)
    print("Escolha:", choice)
    print(sol.pretty())

    # 1) Deve respeitar Tmax em todas as viagens
    for k in range(inst.K):
        for trip in sol.routes[k]:
            assert sol.trip_respects_Tmax(trip), f"Tmax violado no veículo {k}: {trip}"

    # 2) A solução deve conter:
    #    - uma viagem [0,2,0] em algum veículo, OU
    #    - inserção do 2 na viagem do veículo 0 (0->2->1->0 ou 0->1->2->0)
    all_trips = flatten_routes(sol.routes)
    has_new_trip_any = any(trip == [0, 2, 0] for trip in all_trips)
    inserted_in_v0 = any(trip in ([0, 2, 1, 0], [0, 1, 2, 0]) for trip in sol.routes[0])

    # debug adicional para evitar dúvidas
    print("Todas as viagens:", all_trips)

    assert has_new_trip_any or inserted_in_v0, "Nem inseriu 2 em v0 nem abriu viagem nova 0->2->0."
    print("[OK] melhor inserção na frota aplicada e válida.")

if __name__ == "__main__":
    main()
