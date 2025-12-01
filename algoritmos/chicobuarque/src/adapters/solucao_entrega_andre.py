# src/adapters/solucao_entrega_andre.py
from __future__ import annotations
from typing import Dict, List, Optional
from andre_repositorio.solucao import Solucao
from src.core.instance import Instance
from src.core.solution import Solution

# Importar logger (opcional, pode ser None se não quiser logging)
try:
    from src.utils.debug_logger import DebugLogger
    _DebugLogger = DebugLogger
except ImportError:
    _DebugLogger = None  # type: ignore

def build_andre_solucao(inst: Instance, sol: Solution, logger = None) -> Solucao:
    """
    Converte Solution (interna) -> Solucao (formato André).
    - 'rota[k][v]' e 'chegada[k][v]' existem para todo v=1..r (podem ser []).
    - 'chegada' é tempo de chegada ANTES do serviço.
    - Viagens encadeadas com Eq.10: v+1 começa após término de v + s0.

    Args:
        inst: Instância do problema
        sol: Solução interna
        logger: Logger opcional para debug
    """
    # Logar início da conversão
    if logger:
        logger.log_conversion_start()

    # cria dicionários vazios (apenas viagens não-vazias serão adicionadas)
    rota: Dict[int, Dict[int, List[int]]] = {k+1: {} for k in range(inst.K)}
    chegada: Dict[int, Dict[int, List[float]]] = {k+1: {} for k in range(inst.K)}

    for k in range(inst.K):
        acc = 0.0  # tempo acumulado: quando o ônibus está pronto para PARTIR (após serviço)
        for v_idx, trip in enumerate(sol.routes.get(k, []), start=1):
            acc_antes = acc  # Guardar valor ANTES do cálculo para logging

            # compute_arrival_times_from_start calcula tempos a partir do momento de PARTIDA
            # arr[0] será o tempo de partida (possivelmente ajustado para janelas)
            arr = sol.compute_arrival_times_from_start(trip, acc)

            # factivel() espera chegada[k][v][0] como tempo de CHEGADA na garagem (antes do serviço).
            # A validação adiciona s[0] ao tempo de chegada ao calcular quando o ônibus pode sair.
            # Portanto, precisamos armazenar: chegada[0] = partida_real - s[0]
            # Assim: validação calcula partida = chegada[0] + s[0] = (partida_real - s[0]) + s[0] = partida_real
            chegada_inicial = arr[0] - float(inst.s[0])

            arr[0] = chegada_inicial

            # grava nas estruturas (v_idx está em 1..len(trips) <= r)
            rota[k+1][v_idx] = trip[:]                      # [0, ..., 0]
            chegada[k+1][v_idx] = [float(t) for t in arr]   # chegada antes do serviço

            # próxima viagem começa após término desta + s0 (Eq.10)
            # arr[-1] é a chegada de volta na garagem, então próxima partida é arr[-1] + s[0]
            acc = arr[-1] + float(inst.s[0])

            # Logar detalhes da conversão
            if logger:
                logger.log_vehicle_conversion(k, v_idx, trip, acc_antes, arr, acc, inst)

    fx = sol.total_cost()

    sol_andre = Solucao()
    sol_andre.rota = rota
    sol_andre.chegada = chegada
    sol_andre.fx = fx
    return sol_andre
