# tests/test_construtivo_limitado_semana2.py
from pathlib import Path
import sys
"""
Teste (Semana 2): integra EvalCounter ao construtivo simples e interrompe
no número de avaliações configurado.
"""

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "andre_repositorio"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from adapters.loader_andre import load_andre_instance
from core.instance import Instance
from core.solution import Solution
from core.eval_counter import EvalCounter

def main():
    # 1) carrega a pequena
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    # 2) define o limite de avaliações (ex.: 5 pra demonstrar)
    counter = EvalCounter(limit=5)

    # 3) construtivo incremental usando a sua API de frota
    sol = Solution.new_empty(inst)
    nodes = list(range(1, min(inst.n, 10) + 1))  # um subconjunto só pra exemplo

    for k in nodes:
        # aplica a melhor inserção (isso altera a solução atual)
        sol.apply_best_insertion_across_fleet(k)

        # calcula a FO da solução ATUAL e contabiliza UMA avaliação
        fx = sol.total_cost()
        stop = counter.check_and_inc(fx, sol_copy_fn=sol.copy)
        print(f"[eval {counter.count}] após inserir {k}: fx={fx:.2f}")

        if stop:
            print("[INFO] limite de avaliações atingido — parar construtivo.")
            break

    # 4) melhor solução vista dentro do limite
    best = counter.best_sol if counter.best_sol is not None else sol
    print(best.pretty())
    print(f"Melhor fx dentro do limite: {counter.best_fx:.2f}")

    # 5) sanity: respeitar Tmax
    for v in range(inst.K):
        for trip in best.routes[v]:
            assert best.trip_respects_Tmax(trip), f"Tmax violado no veículo {v}: {trip}"

    print("[OK] construtivo limitado por avaliações executado com sucesso.")

if __name__ == "__main__":
    main()
