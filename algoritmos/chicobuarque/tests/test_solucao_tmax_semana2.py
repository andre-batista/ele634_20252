# tests/test_solucao_tmax_semana2.py
from pathlib import Path
import sys
"""
Teste (Semana 2): cria viagem simples 0->i->0 e confere se respeita Tmax.
"""

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

    # cria solução e uma viagem para o veículo 0
    sol = Solution.new_empty(inst)
    sol.start_new_trip(vehicle=0)

    # escolhemos o nó 1 (existe em 1..n) e montamos 0 -> 1 -> 0
    sol.add_stop_current_trip(vehicle=0, node=1)
    sol.finish_current_trip(vehicle=0)

    print(sol.pretty())

    # pega a viagem construída
    trip = sol.routes[0][0]
    t = sol.compute_trip_time(trip)
    print(f"Tempo da viagem: {t:.2f}  | Tmax={inst.Tmax:.2f}")

    assert sol.trip_respects_Tmax(trip), "Viagem 0->1->0 estourou Tmax!"
    print("[OK] viagem simples respeita Tmax.")

if __name__ == "__main__":
    main()
