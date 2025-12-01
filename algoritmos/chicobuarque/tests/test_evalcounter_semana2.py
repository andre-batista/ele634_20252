# tests/test_evalcounter_semana2.py
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
from core.eval_counter import EvalCounter
"""
Teste (Semana 2): demonstra o uso do EvalCounter — para o laço exatamente
no limite de avaliações e guarda a melhor solução observada.
"""

def main():
    # carrega instância pequena
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    # limite de avaliações bem baixo só pra demonstrar
    counter = EvalCounter(limit=3)

    sol = Solution.new_empty(inst)

    # ciclo de "algoritmo": a CADA cálculo de fx, contabilizamos UMA avaliação
    # aqui só vamos abrir viagens unitárias, de propósito
    for node in (1, 2, 3, 4, 5):
        sol.start_new_trip(vehicle=0)
        sol.add_stop_current_trip(vehicle=0, node=node)
        sol.finish_current_trip(vehicle=0)

        fx = sol.total_cost()  # calcula custo ATUAL
        stop = counter.check_and_inc(fx, sol_copy_fn=sol.copy)  # <-- CONTABILIZA AVALIAÇÃO
        print(f"[eval {counter.count}] fx={fx:.2f}")
        if stop:
            print("[INFO] atingiu limite de avaliações, parando laço.")
            break

    # melhor solução encontrada dentro do limite
    best_sol = counter.best_sol if counter.best_sol is not None else sol
    print(best_sol.pretty())
    print(f"Melhor fx dentro do limite: {counter.best_fx:.2f}")

if __name__ == "__main__":
    main()
