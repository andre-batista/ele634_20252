# tests/test_delta_meio_semana2.py
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
Teste (Semana 2): confere Δc/Δt ao inserir um nó entre i->j (no meio da viagem),
comparando com reconstrução literal; valida Tmax.
"""

def main():
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    # começa viagem: 0 -> 1 -> 0
    sol = Solution.new_empty(inst)
    sol.start_new_trip(vehicle=0)
    sol.add_stop_current_trip(0, 1)
    sol.finish_current_trip(0)

    base_trip = sol.routes[0][0]
    base_cost = sol.trip_cost(base_trip)
    base_time = sol.compute_trip_time(base_trip)

    # queremos inserir o nó 2 ENTRE (0 -> 1), ou seja pos=0
    dc, dt = sol.marginal_delta_insert_between(base_trip, pos=0, node=2)

    # checar com reconstrução literal: 0 -> 2 -> 1 -> 0
    new_trip = [0, 2, 1, 0]
    exp_dc = sol.trip_cost(new_trip) - base_cost
    exp_dt = sol.compute_trip_time(new_trip) - base_time

    print(f"Δc calculado={dc:.4f} | Δc esperado={exp_dc:.4f}")
    print(f"Δt calculado={dt:.4f} | Δt esperado={exp_dt:.4f}")

    assert abs(dc - exp_dc) < 1e-9
    assert abs(dt - exp_dt) < 1e-9

    # agora aplica de verdade e checa Tmax
    # recomeça a viagem original para aplicar
    sol = Solution.new_empty(inst)
    sol.start_new_trip(0)
    sol.add_stop_current_trip(0, 1)  # 0->1
    sol.finish_current_trip(0)       # 0->1->0

    dc_apply, dt_apply = sol.insert_between_with_check(vehicle=0, pos=0, node=2)
    print(sol.pretty())

    assert abs(dc - dc_apply) < 1e-9
    assert abs(dt - dt_apply) < 1e-9
    assert sol.trip_respects_Tmax(sol.routes[0][0])

    print("[OK] delta de inserção no meio bate com reconstrução e respeita Tmax.")

if __name__ == "__main__":
    main()
