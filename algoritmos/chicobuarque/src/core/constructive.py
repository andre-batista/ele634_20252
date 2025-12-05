# src/core/constructive.py
"""
Heurísticas Construtivas - GRASP
---------------------------------
Implementa construção de soluções iniciais usando GRASP (Greedy Randomized
Adaptive Search Procedure) integrado à infraestrutura do projeto.

Esta versão valida TODAS as inserções com contexto temporal (Eq. 10):
- Usa o cronograma acumulado do veículo (inclui espera na garagem e s0 entre viagens)
- Garante Tmax e janelas de tempo para a viagem editada E para as seguintes
"""

from __future__ import annotations
import random
from typing import List, Tuple, Optional
from .instance import Instance
from .solution import Solution
from .eval_counter import EvalCounter


# ---------------------------------------------------------------------
# Helpers de viabilidade
# ---------------------------------------------------------------------
def is_trip_feasible_from_start(trip: List[int], start_time: float, inst: Instance, sol: Solution) -> bool:
    """
    Checagem canônica e única de viabilidade de UMA viagem que começa em start_time.
    Usa exatamente o mesmo simulador de chegadas e validação que o validador:
    - Tmax por viagem
    - Janelas de tempo (e, l) para cada nó da trip
    """
    # Tmax
    if not sol.trip_respects_Tmax(trip):
        return False

    # Janelas
    if inst.e is None or inst.l is None:
        return True

    arrival_times = sol.compute_arrival_times_from_start(trip, start_time)
    for idx, node in enumerate(trip):
        if node == 0:
            continue
        arr = float(arrival_times[idx])
        e_i = float(inst.e[node - 1])
        l_i = float(inst.l[node - 1])
        if arr < e_i - 1e-9 or arr > l_i + 1e-9:
            return False
    return True


def _feasible_trip_with_context(sol: Solution, vehicle: int, trip_idx: int, new_trip: List[int]) -> bool:
    """
    Valida new_trip na posição (vehicle, trip_idx) propagando para viagens seguintes,
    sem tocar no objeto 'sol' original (evita poluir caches internos).
    """
    # 1) Clona a solução (cópia profunda o suficiente para ter rotas próprias)
    shadow = sol.copy()

    # 2) Prepara rotas temporárias só no clone
    tmp_routes = {k: [t[:] for t in v] for k, v in shadow.routes.items()}
    if vehicle not in tmp_routes:
        tmp_routes[vehicle] = []

    if trip_idx == len(tmp_routes[vehicle]):
        tmp_routes[vehicle].append(new_trip)
    elif trip_idx < len(tmp_routes[vehicle]):
        tmp_routes[vehicle][trip_idx] = new_trip
    else:
        return False  # índice inválido

    shadow.routes = tmp_routes

    # 3) Valida no clone (propagando Eq.10 a partir de trip_idx)
    ok = shadow.schedule_respects_time_windows_from(vehicle, start_trip_idx=trip_idx)

    # 4) IMPORTANTE: nunca tocar em 'sol' aqui; nada para restaurar
    return ok


def build_rcl(candidates: List[Tuple], alpha: float) -> List[Tuple]:
    """
    Constrói a Lista Restrita de Candidatos (RCL) pelo custo marginal dc.
    Tupla do candidato: (k, t_idx, pos, is_end, dc, dt)
    """
    if not candidates:
        return []

    # Ordena por delta de custo; desempate por delta de tempo
    candidates.sort(key=lambda x: (x[4], x[5]))

    if alpha <= 0.0:
        return [candidates[0]]

    c_min = candidates[0][4]
    c_max = candidates[-1][4]
    threshold = c_min + alpha * (c_max - c_min)
    rcl = [c for c in candidates if c[4] <= threshold]
    return rcl if rcl else [candidates[0]]


# ---------------------------------------------------------------------
# Núcleo: gerar candidatos de inserção VIÁVEIS com Eq. 10
# ---------------------------------------------------------------------
def find_feasible_insertions(sol: Solution, node: int, inst: Instance) -> List[Tuple]:
    """
    Encontra todas as inserções viáveis para 'node' em TODA a frota, considerando:
      - Inserção entre arcos da viagem corrente
      - Inserção no fim (antes do 0)
      - Abertura de nova viagem [0, node, 0] se r permitir

    TODAS as checagens são feitas usando a função canônica
    is_trip_feasible_from_start(...) e, adicionalmente, uma checagem
    COM CONTEXTO (_feasible_trip_with_context) para garantir que
    viagens subsequentes do mesmo veículo continuam viáveis.
    """
    candidates: List[Tuple] = []

    for k in range(inst.K):
        trips = sol.routes[k]
        can_open_new = len(trips) < inst.r

        # (A) Inserir em viagens existentes
        for t_idx, trip in enumerate(trips):
            start_time = sol.get_accumulated_time_for_trip(k, t_idx)

            # Inserir ENTRE arcos
            for pos in range(len(trip) - 1):
                dc, dt = sol.marginal_delta_insert_between(trip, pos, node)
                new_trip = trip[:pos + 1] + [node] + trip[pos + 1:]

                # Checagem canônica por viagem
                if not is_trip_feasible_from_start(new_trip, start_time, inst, sol):
                    continue
                # Checagem com contexto (propaga para viagens seguintes)
                if not _feasible_trip_with_context(sol, k, t_idx, new_trip):
                    continue

                candidates.append((k, t_idx, pos, False, dc, dt))

            # Inserir NO FIM (antes do 0)
            if trip and trip[-1] == 0:
                dc, dt = sol.marginal_delta_insert_end(trip, node)
                new_trip = trip[:-1] + [node, 0]

                if not is_trip_feasible_from_start(new_trip, start_time, inst, sol):
                    pass
                else:
                    if _feasible_trip_with_context(sol, k, t_idx, new_trip):
                        candidates.append((k, t_idx, -1, True, dc, dt))

        # (B) Abrir NOVA VIAGEM [0, node, 0] (voltar à garagem)
        if can_open_new:
            new_trip = [0, node, 0]
            new_t_idx = len(trips)
            start_time = sol.get_accumulated_time_for_trip(k, new_t_idx)

            if is_trip_feasible_from_start(new_trip, start_time, inst, sol):
                if _feasible_trip_with_context(sol, k, new_t_idx, new_trip):
                    dc = inst.c[0][node] + inst.c[node][0]
                    dt = inst.T[0][node] + inst.s[node] + inst.T[node][0]
                    candidates.append((k, new_t_idx, -1, True, dc, dt))

    return candidates


def apply_insertion(sol: Solution, node: int, insertion: Tuple) -> None:
    """
    Aplica a inserção escolhida com uma checagem final de janelas de tempo
    usando o tempo acumulado correto da viagem alvo. Se a checagem falhar,
    a inserção é ignorada (fail-safe).
    """
    k, t_idx, pos, is_end, dc, dt = insertion

    # Caso 1: criar nova viagem (t_idx == -1 ou apontando além do fim)
    if t_idx == -1 or t_idx >= len(sol.routes[k]):
        start_time = sol.get_accumulated_time_for_trip(k, len(sol.routes[k]))
        temp_trip = [0, node, 0]

        if not is_trip_feasible_from_start(temp_trip, start_time, sol.inst, sol):
            return  # descarta candidato inseguro

        sol.start_new_trip(k)
        sol.add_stop_current_trip(k, node)
        sol.finish_current_trip(k)
        return

    # Caso 2: inserir em viagem existente
    trip = sol.routes[k][t_idx]
    if is_end:
        temp_trip = trip[:-1] + [node, 0]
    else:
        temp_trip = trip[:pos + 1] + [node] + trip[pos + 1:]

    start_time = sol.get_accumulated_time_for_trip(k, t_idx)

    if not is_trip_feasible_from_start(temp_trip, start_time, sol.inst, sol):
        return  # descarta candidato inseguro

    # Passou: aplica de fato
    if is_end:
        trip[-1:] = [node, 0]
    else:
        trip[pos + 1:pos + 1] = [node]

# --- DEBUG: dump detalhado do cronograma por veículo/viagem (temporário) ---
'''def _debug_dump_vehicle_schedule(sol: Solution, inst: Instance, k: int) -> None:
    print(f"\n====== DEBUG VEÍCULO k={k+1} ======")
    trips = sol.routes[k]
    for t_idx, trip in enumerate(trips):
        start_time = sol.get_accumulated_time_for_trip(k, t_idx)
        arrs = sol.compute_arrival_times_from_start(trip, start_time)
        print(f"[DBG] k={k} v={t_idx} start={start_time:.1f} trip={trip}")
        if inst.e is not None and inst.l is not None:
            for pos, node in enumerate(trip):
                if node == 0: 
                    continue
                e_i = float(inst.e[node-1]); l_i = float(inst.l[node-1])
                a_i = float(arrs[pos])
                viol = ""
                if a_i < e_i - 1e-9 or a_i > l_i + 1e-9:
                    viol = "  <-- VIOLA JANELA"
                print(f"   node={node:>3}  arr={a_i:6.1f}  win=[{e_i:.1f},{l_i:.1f}]{viol}")
        else:
            for pos, node in enumerate(trip):
                if node != 0:
                    print(f"   node={node:>3}  arr={float(arrs[pos]):6.1f}")

def _debug_dump_all(sol: Solution, inst: Instance) -> None:
    print("\n====== DEBUG COMPLETO (instância média) ======")
    for k in range(inst.K):
        _debug_dump_vehicle_schedule(sol, inst, k)
    print("====== FIM DEBUG COMPLETO ======\n")'''

# ---------------------------------------------------------------------
# Construtor GRASP: usa as inserções viáveis com RCL
# ---------------------------------------------------------------------
def grasp_construction(inst: Instance, alpha: float, counter: EvalCounter,
                       use_time_windows: bool = True, seed: Optional[int] = None) -> Solution:
    """
    Constrói uma solução usando GRASP.
    Conta APENAS UMA avaliação ao FINAL da construção.
    """
    # if seed is not None:
    #     random.seed(seed)

    sol = Solution.new_empty(inst)

    # Definir ordem das requisições
    unvisited = list(range(1, inst.n + 1))
    if use_time_windows and inst.e is not None and inst.l is not None:
        # ordem por abertura de janela ajuda a viabilidade
        unvisited.sort(key=lambda i: inst.e[i - 1])
    else:
        random.shuffle(unvisited)

    # Construção incremental
    for node in unvisited:
        if counter.count >= counter.limit:
            break

        candidates = find_feasible_insertions(sol, node, inst)
        if not candidates:
            # Se não há posição viável para este nó agora, seguimos.
            # (Um reparo posterior pode tentar recolocar.)
            continue

        rcl = build_rcl(candidates, alpha)
        chosen = random.choice(rcl)
        apply_insertion(sol, node, chosen)

    # Uma avaliação ao final
    fx = sol.total_cost()
    counter.check_and_inc(fx, sol_copy_fn=sol.copy)
    # Após construir e avaliar:
    try:
        sol.invalidate_caches()  # ou reset_cache / clear_* se existir
    except AttributeError:
        pass

    # DEBUG: se for a instância média (n=67), despejar cronograma completo
    # if inst.n == 67:
    #     _debug_dump_all(sol, inst)

    return sol


def grasp_multi_start(inst: Instance, n_iterations: int, alpha: float,
                      counter: EvalCounter, use_time_windows: bool = True,
                      verbose: bool = False) -> Solution:
    """
    Executa GRASP múltiplas vezes e retorna a melhor solução encontrada.
    Respeita o limite de avaliações do counter (uma por construção).
    """
    best_sol: Optional[Solution] = None
    best_cost = float('inf')

    for it in range(n_iterations):
        if counter.count >= counter.limit:
            if verbose:
                print(f"[GRASP] Limite de avaliações atingido na iteração {it + 1}/{n_iterations}")
            break

        sol = grasp_construction(inst, alpha, counter, use_time_windows, seed=it)
        cost = sol.total_cost()
        stop = counter.check_and_inc(cost, sol_copy_fn=sol.copy)

        if verbose:
            atendidas = set()
            for k in sol.routes:
                for trip in sol.routes[k]:
                    atendidas.update(n for n in trip if n != 0)
            print(f"[GRASP] Iteração {it + 1}/{n_iterations}: "
                  f"custo={cost:.2f}, reqs={len(atendidas)}/{inst.n}, "
                  f"avaliações={counter.count}/{counter.limit}")

        if cost < best_cost:
            best_sol = sol.copy()
            best_cost = cost
            if verbose:
                print("  ✓ Nova melhor solução!")
        
        if stop:
            break

    return best_sol if best_sol else Solution.new_empty(inst)


# ---------------------------------------------------------------------
# Repair simples (após construção)
# ---------------------------------------------------------------------
def repair_missing_nodes(sol: Solution, inst: Instance, counter: EvalCounter,
                         max_attempts: int = 10) -> Solution:
    """
    Repara solução adicionando nós não atendidos, tentando inserções com contexto.
    Cada reparo bem-sucedido registra UMA avaliação no counter.
    """
    atendidas = set()
    for k in sol.routes:
        for trip in sol.routes[k]:
            atendidas.update(n for n in trip if n != 0)

    missing = set(range(1, inst.n + 1)) - atendidas
    if not missing:
        return sol

    repaired = sol.copy()

    for node in missing:
        if counter.count >= counter.limit:
            break

        for _ in range(max_attempts):
            candidates = find_feasible_insertions(repaired, node, inst)
            if not candidates:
                continue
            # Escolhe o melhor por dc (depois dt)
            best = min(candidates, key=lambda x: (x[4], x[5]))
            apply_insertion(repaired, node, best)

            fx = repaired.total_cost()
            counter.check_and_inc(fx, sol_copy_fn=repaired.copy)
            break

    return repaired


# ---------------------------------------------------------------------
# Estatísticas da solução
# ---------------------------------------------------------------------
def solution_stats(sol: Solution, inst: Instance) -> dict:
    total_trips = 0
    total_nodes = 0
    atendidas = set()
    trip_times = []

    for k in sol.routes:
        total_trips += len(sol.routes[k])
        for trip in sol.routes[k]:
            total_nodes += max(0, len(trip) - 2)
            atendidas.update(n for n in trip if n != 0)
            trip_times.append(sol.compute_trip_time(trip))

    return {
        'custo_total': sol.total_cost(),
        'num_viagens': total_trips,
        'num_nos': total_nodes,
        'requisicoes_atendidas': len(atendidas),
        'requisicoes_total': inst.n,
        'cobertura': len(atendidas) / inst.n if inst.n > 0 else 0.0,
        'tempo_max_viagem': max(trip_times) if trip_times else 0.0,
        'tempo_medio_viagem': (sum(trip_times) / len(trip_times)) if trip_times else 0.0,
        'violacoes_tmax': sum(1 for t in trip_times if t > inst.Tmax + 1e-9),
    }
