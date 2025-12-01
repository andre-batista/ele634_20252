# tests/test_best_insercao_semana2.py
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
Teste (Semana 2): “melhor inserção” dentro de uma viagem, comparada com
força-bruta (varre todas as posições viáveis) e checa aplicação única.
"""

def brute_force_best(sol: Solution, trip: list[int], node: int):
    """Calcula melhor Δc/Δt por força bruta para conferir a API."""
    best = None
    base_cost = sol.trip_cost(trip)
    base_time = sol.compute_trip_time(trip)

    # entre arcos
    for pos in range(len(trip) - 1):
        new_trip = trip[:pos+1] + [node] + trip[pos+1:]
        if sol.trip_respects_Tmax(new_trip):
            dc = sol.trip_cost(new_trip) - base_cost
            dt = sol.compute_trip_time(new_trip) - base_time
            cand = (pos, False, dc, dt)
            if (best is None) or (dc < best[2] - 1e-12) or (abs(dc - best[2]) <= 1e-12 and dt < best[3]):
                best = cand

    # no fim
    if trip and trip[-1] == 0:
        new_trip = trip[:-1] + [node, 0]
        if sol.trip_respects_Tmax(new_trip):
            dc = sol.trip_cost(new_trip) - base_cost
            dt = sol.compute_trip_time(new_trip) - base_time
            cand = (-1, True, dc, dt)
            if (best is None) or (dc < best[2] - 1e-12) or (abs(dc - best[2]) <= 1e-12 and dt < best[3]):
                best = cand

    return best

def main():
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    sol = Solution.new_empty(inst)
    sol.start_new_trip(vehicle=0)
    sol.add_stop_current_trip(0, 1)   # 0->1
    sol.finish_current_trip(0)        # 0->1->0

    trip = sol.routes[0][0]
    base_trip = trip.copy()  # snapshot imutável

    # 1) escolher a melhor inserção sem modificar a rota
    best_api  = sol.best_insertion_in_trip(base_trip, node=2)
    best_brut = brute_force_best(sol, base_trip, 2)

    print("API  :", best_api)
    print("Brute:", best_brut)
    assert best_api is not None and best_brut is not None
    assert abs(best_api[2] - best_brut[2]) < 1e-9
    assert abs(best_api[3] - best_brut[3]) < 1e-9

    # 2) aplicar UMA vez e comparar com a rota esperada construída a partir do snapshot
    pos, is_end, _, _ = sol.apply_best_insertion_in_trip(vehicle=0, node=2)

    if is_end:
        expected_trip = base_trip[:-1] + [2, 0]
    else:
        expected_trip = base_trip[:pos+1] + [2] + base_trip[pos+1:]

    print(sol.pretty())
    assert sol.routes[0][0] == expected_trip
    assert sol.trip_respects_Tmax(sol.routes[0][0])

    print("[OK] melhor inserção bate com força bruta, aplica 1x e respeita Tmax.")

if __name__ == "__main__":
    main()
