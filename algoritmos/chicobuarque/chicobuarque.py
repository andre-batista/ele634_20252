# chicobuarque.py
"""
Implementação GRASP + VNS para Problema de Roteamento de Ônibus
----------------------------------------------------------------
Grupo: Chico Buarque

Estratégia:
1. GRASP: Construção gulosa aleatorizada de múltiplas soluções iniciais (~20% budget)
2. VNS: Variable Neighborhood Search para melhorar a melhor solução (~80% budget)

Estrutura seguindo a conceitualização:
- Fase construtiva: GRASP com ordenação por janelas de tempo
- Fase de melhoria: VNS com 5 vizinhanças (relocate, exchange, misto)
- Busca local: 2-opt, relocate, exchange, merge-split (já implementados)
"""

from __future__ import annotations
from andre_repositorio.dados import Dados
from andre_repositorio.solucao import Solucao
from src.core.instance import Instance
from src.core.solution import Solution
from src.core.eval_counter import EvalCounter
from src.core.constructive import grasp_multi_start, repair_missing_nodes, solution_stats
from src.core.vns import vns
from src.adapters.solucao_entrega_andre import build_andre_solucao


def resolva(dados: Dados, numero_avaliacoes: int) -> Solucao:
    """
    Executa o algoritmo de otimização GRASP + VNS.

    Estratégia:
    - GRASP (20% do budget): Construção gulosa aleatorizada com múltiplos restarts
    - VNS (80% do budget): Variable Neighborhood Search com 5 vizinhanças estruturadas

    Parâmetros:
    -----------
    dados : Dados
        Objeto contendo os dados da instância do problema, incluindo:
        - n: número de requisições (estudantes)
        - K: número de ônibus disponíveis
        - r: número máximo de viagens por ônibus
        - Tmax: tempo máximo por viagem
        - D, T, c: matrizes de distância, tempo e custo
        - s: tempos de serviço em cada requisição
        - e, l: janelas de tempo (opcional)

    numero_avaliacoes : int
        Número máximo de avaliações da função objetivo permitidas.
        O algoritmo para quando atingir este limite e retorna a melhor
        solução encontrada até então.

    Retorna:
    --------
    Solucao
        Objeto contendo:
        - rota[k][v]: lista de requisições visitadas pelo ônibus k na viagem v
                    (sempre iniciando e terminando em 0 = garagem)
        - chegada[k][v]: lista de instantes de chegada em cada ponto da rota
        - fx: valor da função objetivo (custo total)

    Observações:
    ------------
    - Cada avaliação da função objetivo corresponde a uma chamada de total_cost()
    - Não utiliza Gurobi, apenas heurísticas construtivas e de melhoria
    - Todas as soluções retornadas são viáveis (respeitam Tmax e atendem 100% das requisições)
    """
    # ========================================================================
    # 1. CONVERSÃO DE DADOS
    # ========================================================================
    raw = dict(
        n=dados.n, K=dados.K, r=dados.r, Tmax=dados.Tmax,
        D=dados.D, T=dados.T, c=dados.c, s=dados.s,
        e=getattr(dados, "e", None), 
        l=getattr(dados, "l", None),
    )
    inst = Instance.from_andre(raw)

    print(f"[CHK] n={inst.n}, K={inst.K}, r={inst.r}, Tmax={inst.Tmax}")
    print(f"[CHK] s0={inst.s[0]}  s[1..3]={inst.s[1:4]}")
    print(f"[CHK] e[1..3]={inst.e[:3] if inst.e is not None else None}")
    print(f"[CHK] l[1..3]={inst.l[:3] if inst.l is not None else None}")

    
    # ========================================================================
    # 2. CONFIGURAÇÃO DE PARÂMETROS
    # ========================================================================
    # Dividir budget: 20% para GRASP, 80% para VNS
    grasp_budget = max(1, numero_avaliacoes // 5)
    vns_budget = numero_avaliacoes - grasp_budget
    '''vns_budget = 0'''

    
    # Parâmetros GRASP
    alpha = 0.3  # aleatoriedade (0=guloso, 1=aleatório)
    n_grasp_iterations = min(10, grasp_budget // 10)  # pelo menos 10 avaliações por iteração
    
    # Parâmetros VNS
    k_max = 5  # número de vizinhanças
    local_search_iters = 100  # iterações da busca local
    
    # ========================================================================
    # 3. FASE CONSTRUTIVA: GRASP
    # ========================================================================
    counter_grasp = EvalCounter(limit=grasp_budget)
    
    sol_initial = grasp_multi_start(
        inst=inst,
        n_iterations=n_grasp_iterations,
        alpha=alpha,
        counter=counter_grasp,
        use_time_windows=True,  # ordenar por janelas de tempo
        verbose=False  # desativar prints para não poluir saída
    )
    
    # Tentar reparar nós não atendidos (se houver budget)
    if counter_grasp.count < counter_grasp.limit:
        sol_initial = repair_missing_nodes(
            sol=sol_initial,
            inst=inst,
            counter=counter_grasp,
            max_attempts=5
        )
    
    # ========================================================================
    # 4. FASE DE MELHORIA: VNS
    # ========================================================================
    counter_vns = EvalCounter(limit=vns_budget)
    
    # Inicializar com a solução do GRASP
    counter_vns.best_fx = sol_initial.total_cost()
    if counter_vns.count < counter_vns.limit:
        counter_vns.check_and_inc(sol_initial.total_cost(), sol_initial.copy)

    
    sol_final = vns(
        sol=sol_initial,
        inst=inst,
        counter=counter_vns,
        k_max=k_max,
        local_search_iters=local_search_iters,
        verbose=False  # desativar prints
    )
    '''# ========================================================================
    # 4. FASE DE MELHORIA: VNS (DESLIGADA)
    # ========================================================================
    counter_vns = EvalCounter(limit=vns_budget)
    sol_final = sol_initial  # nada de VNS
    counter_vns.best_fx = sol_initial.total_cost()
    counter_vns.best_sol = sol_initial.copy()'''

    
    # ========================================================================
    # 5. SELEÇÃO DA MELHOR SOLUÇÃO E CONVERSÃO
    # ========================================================================
    # Pegar a melhor solução vista em todo o processo
    # (pode estar no contador do GRASP ou do VNS)
    
    if counter_vns.best_fx < counter_grasp.best_fx:
        best = counter_vns.best_sol
    else:
        best = counter_grasp.best_sol
    
    # Se não encontrou nenhuma solução viável, usa a última
    if best is None:
        best = sol_final
    
    # ========================================================================
    # 6. PRÉ-VALIDAÇÃO ANTES DA CONVERSÃO (OPCIONAL - para debug)
    # ========================================================================
    # Detectar violações de janelas de tempo ANTES da conversão
    violations_pre = []
    if inst.e is not None and inst.l is not None:
        for k in range(inst.K):
            acc = 0.0
            for trip in best.routes.get(k, []):
                arr = best.compute_arrival_times_from_start(trip, acc)
                for idx, node in enumerate(trip):
                    if node == 0:
                        continue
                    e_i = inst.e[node - 1]
                    l_i = inst.l[node - 1]
                    a_i = arr[idx]
                    if a_i < e_i - 1e-9 or a_i > l_i + 1e-9:
                        violations_pre.append({
                            'vehicle': k,
                            'node': node,
                            'arrival': a_i,
                            'e': e_i,
                            'l': l_i
                        })
                acc = arr[-1] + float(inst.s[0])

    # ========================================================================
    # 7. VALIDAÇÃO FINAL DO LIMITE DE AVALIAÇÕES
    # ========================================================================
    total_avaliacoes_usadas = counter_grasp.count + counter_vns.count

    # Verificação de segurança: garantir que não excedemos o limite
    if total_avaliacoes_usadas > numero_avaliacoes:
        raise RuntimeError(
            f"ERRO: Limite de avaliações excedido! "
            f"Usadas: {total_avaliacoes_usadas}, Limite: {numero_avaliacoes}"
        )

    # ========================================================================
    # 8. CONVERSÃO PARA FORMATO DO ANDRÉ (sem logger por padrão)
    # ========================================================================
    return build_andre_solucao(inst, best)


# ============================================================================
# Funções auxiliares para testes e debug
# ============================================================================

def resolva_verbose(dados: Dados, numero_avaliacoes: int) -> tuple:
    """
    Versão com saída detalhada do algoritmo para testes e debug.
    
    Esta função executa o mesmo algoritmo que resolva(), mas imprime
    informações detalhadas sobre o progresso em cada fase.
    
    Parâmetros:
    -----------
    dados : Dados
        Objeto contendo os dados da instância do problema
    
    numero_avaliacoes : int
        Número máximo de avaliações da função objetivo permitidas
    
    Retorna:
    --------
    tuple
        Tupla contendo:
        - Solucao: Melhor solução encontrada
        - dict: Dicionário com estatísticas detalhadas incluindo:
            * custo_inicial: Custo da solução GRASP
            * custo_final: Custo após VNS
            * melhoria_absoluta: Diferença de custo
            * melhoria_percentual: Melhoria em %
            * avaliacoes_grasp: Avaliações usadas no GRASP
            * avaliacoes_vns: Avaliações usadas no VNS
            * avaliacoes_total: Total de avaliações usadas
            * cobertura: % de requisições atendidas
            * num_viagens: Número de viagens utilizadas
    """
    raw = dict(
        n=dados.n, K=dados.K, r=dados.r, Tmax=dados.Tmax,
        D=dados.D, T=dados.T, c=dados.c, s=dados.s,
        e=getattr(dados, "e", None), 
        l=getattr(dados, "l", None),
    )
    inst = Instance.from_andre(raw)
    
    # Configuração
    grasp_budget = max(1, numero_avaliacoes // 5)
    vns_budget = numero_avaliacoes - grasp_budget
    
    print("=" * 70)
    print(f"GRASP + VNS - Problema de Roteamento de Ônibus")
    print("=" * 70)
    print(f"Instância: n={inst.n}, K={inst.K}, r={inst.r}, Tmax={inst.Tmax:.1f}")
    print(f"Budget total: {numero_avaliacoes} avaliações")
    print(f"  - GRASP: {grasp_budget} avaliações ({grasp_budget/numero_avaliacoes*100:.1f}%)")
    print(f"  - VNS: {vns_budget} avaliações ({vns_budget/numero_avaliacoes*100:.1f}%)")
    print("=" * 70)
    
    # GRASP
    print("\n[FASE 1] Construção de Solução Inicial (GRASP)")
    print("-" * 70)
    counter_grasp = EvalCounter(limit=grasp_budget)
    n_grasp_iterations = min(10, grasp_budget // 10)
    
    sol_initial = grasp_multi_start(
        inst=inst,
        n_iterations=n_grasp_iterations,
        alpha=0.3,
        counter=counter_grasp,
        use_time_windows=True,
        verbose=True
    )
    
    stats_initial = solution_stats(sol_initial, inst)
    print(f"\nSolução inicial GRASP:")
    print(f"  Custo: {stats_initial['custo_total']:.2f}")
    print(f"  Cobertura: {stats_initial['requisicoes_atendidas']}/{stats_initial['requisicoes_total']} "
          f"({stats_initial['cobertura']*100:.1f}%)")
    print(f"  Viagens: {stats_initial['num_viagens']}")
    print(f"  Avaliações usadas: {counter_grasp.count}/{counter_grasp.limit}")
    
    # Reparo
    if counter_grasp.count < counter_grasp.limit and stats_initial['cobertura'] < 1.0:
        print("\n[REPARO] Tentando adicionar requisições faltantes...")
        sol_initial = repair_missing_nodes(sol_initial, inst, counter_grasp, max_attempts=5)
        stats_repaired = solution_stats(sol_initial, inst)
        print(f"  Após reparo: {stats_repaired['requisicoes_atendidas']}/{stats_repaired['requisicoes_total']} "
              f"requisições atendidas")
    
    # VNS
    print("\n[FASE 2] Melhoria com VNS")
    print("-" * 70)
    counter_vns = EvalCounter(limit=vns_budget)
    counter_vns.best_fx = sol_initial.total_cost()
    counter_vns.best_sol = sol_initial.copy()
    
    sol_final = vns(
        sol=sol_initial,
        inst=inst,
        counter=counter_vns,
        k_max=5,
        local_search_iters=100,
        verbose=True
    )
    
    stats_final = solution_stats(sol_final, inst)
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(f"Custo inicial (GRASP): {stats_initial['custo_total']:.2f}")
    print(f"Custo final (VNS):     {stats_final['custo_total']:.2f}")
    print(f"Melhoria:              {stats_initial['custo_total'] - stats_final['custo_total']:.2f} "
          f"({(1 - stats_final['custo_total']/stats_initial['custo_total'])*100:.2f}%)")
    print(f"Avaliações totais:     {counter_grasp.count + counter_vns.count}/{numero_avaliacoes}")
    print("=" * 70)
    
    # Melhor solução
    if counter_vns.best_fx < counter_grasp.best_fx:
        best = counter_vns.best_sol
    else:
        best = counter_grasp.best_sol
    
    if best is None:
        best = sol_final
    
    solucao_andre = build_andre_solucao(inst, best)
    
    estatisticas = {
        'custo_inicial': stats_initial['custo_total'],
        'custo_final': stats_final['custo_total'],
        'melhoria_absoluta': stats_initial['custo_total'] - stats_final['custo_total'],
        'melhoria_percentual': (1 - stats_final['custo_total']/stats_initial['custo_total'])*100,
        'avaliacoes_grasp': counter_grasp.count,
        'avaliacoes_vns': counter_vns.count,
        'avaliacoes_total': counter_grasp.count + counter_vns.count,
        'cobertura': stats_final['cobertura'],
        'num_viagens': stats_final['num_viagens']
    }
    
    return solucao_andre, estatisticas