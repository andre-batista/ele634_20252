# src/core/eval_counter.py
from __future__ import annotations
from copy import deepcopy
from typing import Any, Optional, Callable

"""
EvalCounter
-----------
Contador de avaliações da função-objetivo.

Finalidade:
- Garantir o critério de parada por número de avaliações (numero_avaliacoes).
- Após calcular um custo (fx), chame `check_and_inc(fx, sol_copy_fn=...)`.
- O contador registra a melhor solução observada e informa quando parar.

Uso típico:
    counter = EvalCounter(limit=numero_avaliacoes)
    fx = sol.total_cost()
    if counter.check_and_inc(fx, sol_copy_fn=sol.copy):
        break
"""

class EvalCounter:
    """
    Controla o limite de avaliações da função-objetivo.
    Use check_and_inc(fx, sol_copy_fn=...) logo após calcular um custo.
    """
    def __init__(self, limit: int):
        self.limit = int(limit)
        self.count = 0
        self.best_fx = float("inf")
        self.best_sol = None

    def check_and_inc(self, fx: float, sol_copy_fn: Optional[Callable[[], Any]] = None) -> bool:
        """
        Registra 1 avaliação e atualiza a melhor solução se melhorar.
        Retorna True se atingiu o limite e você deve PARAR o algoritmo.
        """
        self.count += 1
        if fx < self.best_fx:
            self.best_fx = fx
            self.best_sol = deepcopy(sol_copy_fn()) if sol_copy_fn else None
        return self.count >= self.limit
