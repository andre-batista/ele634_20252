# tests/test_solucao_dummy_semana2.py
from pathlib import Path
import sys
"""
Teste (Semana 2): monta uma solução dummy (cada veículo 0->0) e imprime.
Objetivo: garantir que a impressão/estrutura de Solution funciona.
"""

# paths p/ imports de src/ e andre_repositorio/
ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "andre_repositorio"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from adapters.loader_andre import load_andre_instance
from core.instance import Instance
from core.solution import Solution  # já existe o arquivo no seu repo

def main():
    # carrega instância pequena
    raw = load_andre_instance(str(ROOT / "andre_repositorio" / "dados" / "pequena.json"))
    inst = Instance.from_andre(raw)

    # cria solução dummy: cada veículo faz 1 viagem vazia 0->0
    sol = Solution.new_empty(inst)
    for k in range(inst.K):
        sol.start_new_trip(vehicle=k)      # inicia viagem do veículo k no depósito
        sol.finish_current_trip(vehicle=k) # volta p/ depósito sem atender ninguém

    # imprime em formato amigável
    print(sol.pretty())

    # checagem básica: custo e tempo devem ser zero na dummy
    assert abs(sol.total_cost()) < 1e-9
    assert all(t == 0 for t in sol.trip_times()), "viagens não deveriam ter tempo > 0"

    print("[OK] solução dummy construída e validada.")

if __name__ == "__main__":
    main()
