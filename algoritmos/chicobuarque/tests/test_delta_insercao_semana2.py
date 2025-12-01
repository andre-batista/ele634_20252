# tests/test_delta_insercao_semana2.py
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

def main():
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    sol = Solution.new_empty(inst)
    sol.start_new_trip(vehicle=0)          # começa 0
    sol.add_stop_current_trip(0, 1)        # 0 -> 1
    sol.finish_current_trip(0)             # 0 -> 1 -> 0

    trip = sol.routes[0][0]
    base_cost = sol.trip_cost(trip)
    base_time = sol.compute_trip_time(trip)

    # calcular delta para inserir nó 2 no fim: 0 -> 1 -> 2 -> 0
    dc, dt = sol.marginal_delta_insert_end(trip, node=2)

    # custo/tempo esperado por reconstrução literal
    expected_cost = sol.trip_cost([0,1,2,0]) - base_cost
    expected_time = sol.compute_trip_time([0,1,2,0]) - base_time

    print(f"Δc calculado={dc:.4f} | Δc esperado={expected_cost:.4f}")
    print(f"Δt calculado={dt:.4f} | Δt esperado={expected_time:.4f}")

    assert abs(dc - expected_cost) < 1e-9
    assert abs(dt - expected_time) < 1e-9

    # agora aplica de verdade e checa Tmax
    dc_aplicado, dt_aplicado = sol.add_stop_end_with_check(0, 2)
    print(sol.pretty())
    assert abs(dc - dc_aplicado) < 1e-9
    assert abs(dt - dt_aplicado) < 1e-9
    assert sol.trip_respects_Tmax(sol.routes[0][0])

    print("[OK] delta de inserção no fim bate com reconstrução e respeita Tmax.")

if __name__ == "__main__":
    main()
