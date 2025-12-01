# src/core/vns.py
"""
Variable Neighborhood Search (VNS) - VERSÃO COMPLETA
-----------------------------------------------------
Implementa VNS estruturado com vizinhanças hierárquicas.

Vizinhanças (k=1..5):
- k=1: Busca local intra-viagem (2-opt + relocate intra)
- k=2: Relocate inter-viagens
- k=3: Exchange inter-viagens
- k=4: Merge-split de viagens
- k=5: Combinação de todas as buscas
"""

from __future__ import annotations
import random
from typing import Optional
from .instance import Instance
from .solution import Solution
from .eval_counter import EvalCounter

# Contador global para logging (apenas para debug)
_ensure_integrity_call_count = 0


def ensure_route_integrity(sol: Solution, inst: Instance, logger=None) -> None:
    """
    Garante que todas as rotas começam e terminam em 0.
    Remove 0s duplicados no meio da rota.

    IMPORTANTE: Esta função apenas limpa o formato das rotas (remove 0s duplicados).
    NÃO deve invalidar restrições temporais ou de Tmax.

    Args:
        sol: Solução a ser limpa
        inst: Instância
        logger: Logger opcional para debug
    """
    global _ensure_integrity_call_count
    _ensure_integrity_call_count += 1

    if logger:
        logger.log_vns_integrity_call(_ensure_integrity_call_count)
    for k in range(inst.K):
        for t_idx in range(len(sol.routes[k])):
            trip = sol.routes[k][t_idx]
            if not trip:
                continue
            
            # Garantir que começa em 0
            if trip[0] != 0:
                trip.insert(0, 0)
            
            # Garantir que termina em 0
            if trip[-1] != 0:
                trip.append(0)
            
            # Remover 0s do meio (mantém apenas primeiro e último)
            cleaned = [0]  # primeiro 0
            for i in range(1, len(trip) - 1):
                if trip[i] != 0:
                    cleaned.append(trip[i])
            cleaned.append(0)  # último 0
            
            sol.routes[k][t_idx] = cleaned


def light_perturbation(sol: Solution, inst: Instance, intensity: int = 1, logger=None) -> Solution:
    """
    Aplica uma perturbação leve na solução (shaking).
    
    Args:
        sol: Solução a perturbar
        inst: Instância
        intensity: Intensidade da perturbação (1-3)
    
    Returns:
        Solução perturbada
    """
    perturbed = sol.copy()
    
    # Aplicar 1-3 movimentos aleatórios
    num_moves = intensity
    
    for _ in range(num_moves):
        # Escolher operação aleatória
        op = random.choice(['relocate', 'exchange', 'swap'])
        
        if op == 'relocate':
            # Relocate aleatório
            ok, _ = perturbed.relocate_inter_once()
        elif op == 'exchange':
            # Exchange aleatório
            ok, _ = perturbed.exchange_inter_once()
        else:
            # Swap de duas viagens pequenas
            vehicles = [k for k in range(inst.K) if len(perturbed.routes[k]) >= 2]
            if vehicles:
                k = random.choice(vehicles)
                if len(perturbed.routes[k]) >= 2:
                    t1, t2 = random.sample(range(len(perturbed.routes[k])), 2)
                    perturbed.routes[k][t1], perturbed.routes[k][t2] = \
                        perturbed.routes[k][t2], perturbed.routes[k][t1]

    ensure_route_integrity(perturbed, inst, logger)

    # CORREÇÃO DO BUG: Validar cronograma completo após perturbação
    # Se a perturbação invalidou janelas de tempo (considerando tempo acumulado),
    # retornar cópia da solução original ao invés da perturbada
    if not perturbed.validate_full_schedule():
        if logger:
            logger.log("vns_integrity", "⚠️  Perturbação invalidou cronograma - revertendo")
        return sol.copy()

    return perturbed


def apply_neighborhood_search(sol: Solution, k: int, max_iter: int = 100, logger=None) -> Solution:
    """
    Aplica busca local específica da vizinhança k.

    Args:
        sol: Solução inicial
        k: Índice da vizinhança (1-5)
        max_iter: Número máximo de iterações

    Returns:
        Solução melhorada
    """
    improved = sol.copy()

    if k == 1:
        # Vizinhança 1: Busca intra-viagem (2-opt + relocate intra)
        improved.local_search_intra(max_iter=max_iter)

    elif k == 2:
        # Vizinhança 2: Relocate inter-viagens
        iteration = 0
        while iteration < max_iter:
            ok, gain = improved.relocate_inter_once()
            if not ok:
                break
            iteration += 1

    elif k == 3:
        # Vizinhança 3: Exchange inter-viagens
        iteration = 0
        while iteration < max_iter:
            ok, gain = improved.exchange_inter_once()
            if not ok:
                break
            iteration += 1

    elif k == 4:
        # Vizinhança 4: Merge-split
        iteration = 0
        improved_merge_split = True
        while iteration < max_iter and improved_merge_split:
            improved_merge_split = False

            # Tentar merges
            for vehicle in range(improved.inst.K):
                t = 0
                while t + 1 < len(improved.routes[vehicle]):
                    ok, gain = improved.merge_two_trips_if_better(vehicle, t, t + 1)
                    if ok:
                        improved_merge_split = True
                    else:
                        t += 1

            # Tentar splits
            for vehicle in range(improved.inst.K):
                for t_idx in range(len(improved.routes[vehicle])):
                    ok, gain = improved.split_trip_if_better(vehicle, t_idx)
                    if ok:
                        improved_merge_split = True
                        break

            iteration += 1

    else:  # k == 5
        # Vizinhança 5: Combinação de todas (busca completa)
        # Primeiro intra, depois inter
        improved.local_search_intra(max_iter=max_iter // 2)
        improved.local_search_inter(
            allow_relocate=True,
            allow_exchange=True,
            allow_merge_split=True,
            max_iter=max_iter // 2
        )

    ensure_route_integrity(improved, improved.inst, logger)

    # CORREÇÃO DO BUG: Validar cronograma completo após busca de vizinhança
    # Se a busca invalidou janelas de tempo (considerando tempo acumulado),
    # retornar cópia da solução original ao invés da melhorada
    if not improved.validate_full_schedule():
        if logger:
            logger.log("vns_integrity", f"⚠️  Vizinhança k={k} invalidou cronograma - revertendo")
        return sol.copy()

    return improved


def vns(sol: Solution, inst: Instance, counter: EvalCounter,
        k_max: int = 5, local_search_iters: int = 100,
        verbose: bool = False, logger=None) -> Solution:
    """
    Variable Neighborhood Search com vizinhanças estruturadas.
    
    Vizinhanças:
    - k=1: Busca intra-viagem (2-opt + relocate intra)
    - k=2: Relocate inter-viagens
    - k=3: Exchange inter-viagens
    - k=4: Merge-split
    - k=5: Busca completa (intra + inter)
    
    Args:
        sol: Solução inicial
        inst: Instância
        counter: Contador de avaliações
        k_max: Número de vizinhanças (1-5)
        local_search_iters: Iterações por busca local
        verbose: Imprimir progresso
    
    Returns:
        Melhor solução encontrada
    """
    # Garantir integridade da solução inicial
    ensure_route_integrity(sol, inst, logger)
    
    best = sol.copy()
    best_cost = best.total_cost()

    if counter.count < counter.limit:
        counter.check_and_inc(best_cost, sol_copy_fn=best.copy)

    if verbose:
        print(f"[VNS] Iniciando com custo={best_cost:.2f}")
    
    k = 1
    iteration = 0
    
    while k <= k_max and counter.count < counter.limit:
        iteration += 1
        
        # 1. SHAKING: Perturbação leve (proporcional a k)
        intensity = min(k, 3)
        sol_shake = light_perturbation(best, inst, intensity, logger)

        # 2. LOCAL SEARCH: Busca específica da vizinhança k
        sol_local = apply_neighborhood_search(sol_shake, k, local_search_iters, logger)
        
        # 3. AVALIAÇÃO
        cost = sol_local.total_cost()
        
        # Contar avaliação
        if counter.check_and_inc(cost, sol_copy_fn=sol_local.copy):
            if verbose:
                print(f"[VNS] Limite de avaliações atingido: {counter.count}/{counter.limit}")
            break
        
        # 4. MOVIMENTO OU MUDANÇA DE VIZINHANÇA
        if cost < best_cost - 1e-9:
            best = sol_local.copy()
            best_cost = cost
            k = 1  # Reinicia na primeira vizinhança
            
            if verbose:
                print(f"[VNS] Iteração {iteration}, k={k}: "
                      f"Melhoria! Novo custo={best_cost:.2f}, "
                      f"avaliações={counter.count}/{counter.limit}")
        else:
            k += 1  # Próxima vizinhança
            
            if verbose and k <= k_max:
                print(f"[VNS] Iteração {iteration}: Sem melhoria com k={k-1}, "
                      f"mudando para vizinhança k={k}")
    
    if verbose:
        print(f"[VNS] Finalizado: custo={best_cost:.2f}, "
              f"iterações={iteration}, avaliações={counter.count}/{counter.limit}")
    
    return best


def vns_with_restarts(sol: Solution, inst: Instance, counter: EvalCounter,
                       k_max: int = 5, num_restarts: int = 3,
                       local_search_iters: int = 100,
                       verbose: bool = False) -> Solution:
    """
    VNS com múltiplos restarts para escapar de ótimos locais.
    """
    best_global = sol.copy()
    best_cost = best_global.total_cost()
    if counter.count < counter.limit:
        counter.check_and_inc(best_cost, sol_copy_fn=best_global.copy)

    budget_per_restart = counter.limit // (num_restarts + 1)
    
    for restart in range(num_restarts):
        if counter.count >= counter.limit:
            break
        
        if verbose:
            print(f"\n[VNS-RESTART] Restart {restart+1}/{num_restarts}")
        
        # Criar sub-contador
        sub_counter = EvalCounter(limit=min(budget_per_restart, 
                                            counter.limit - counter.count))
        
        # Solução inicial para este restart
        if restart == 0:
            current_sol = sol.copy()
        else:
            # Perturbação forte para diversificar
            current_sol = light_perturbation(best_global, inst, intensity=5)
        
        # VNS neste restart
        improved_sol = vns(current_sol, inst, sub_counter, k_max, 
                          local_search_iters, verbose)
        
        # Atualizar contador global
        counter.count += sub_counter.count
        
        # Atualizar melhor global
        improved_cost = improved_sol.total_cost()
        if improved_cost < best_cost - 1e-9:
            best_global = improved_sol.copy()
            best_cost = improved_cost
            
            if verbose:
                print(f"[VNS-RESTART] Nova melhor global: {best_cost:.2f}")
    
    return best_global


def analyze_neighborhoods(sol: Solution, inst: Instance) -> dict:
    """
    Analisa as vizinhanças disponíveis para a solução.
    """
    stats = {
        'num_internal_nodes': 0,
        'num_trips': 0,
        'avg_trip_size': 0.0,
        'possible_relocates': 0,
        'possible_exchanges': 0
    }
    
    total_nodes = 0
    total_trips = 0
    
    for k in sol.routes:
        total_trips += len(sol.routes[k])
        for trip in sol.routes[k]:
            internal = len(trip) - 2
            total_nodes += internal
    
    stats['num_internal_nodes'] = total_nodes
    stats['num_trips'] = total_trips
    stats['avg_trip_size'] = total_nodes / total_trips if total_trips > 0 else 0.0
    
    stats['possible_relocates'] = total_nodes * (total_trips * 3)
    stats['possible_exchanges'] = (total_nodes * (total_nodes - 1)) // 2
    
    return stats