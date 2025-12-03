import random
import sys
import time
from typing import List
from Dados import Dados, carrega_dados_json
from solucao import Solucao as SolucaoFinal
from Solution import Solution as VnsSolution
from VNS import VariableNeighborhoodSearch
from Neighborhood import (TwoOpt, RemoveAndReinsert, InterTripSwap, MergeTrips, SwapTripsBetweenBuses, SplitTrip)

def _traduzir_solucao(sua_solucao: VnsSolution, dados: Dados) -> SolucaoFinal:    
    # 1. Cria a instância de saída vazia
    solucao_final = SolucaoFinal()
    
    # 2. Define a função objetivo
    solucao_final.fx = sua_solucao.total_cost
    
    num_onibus_total = dados.K
    num_viagens_total = dados.r
    
    # 3. Itera sobre ônibus (base 0) para preencher (base 1)
    for k_idx in range(num_onibus_total):
        k_prof = k_idx + 1  # Índice do professor (base 1)
        
        # Cria os dicionários internos para este ônibus
        solucao_final.rota[k_prof] = {}
        solucao_final.chegada[k_prof] = {}
        
        num_viagens_feitas_por_este_onibus = 0
        
        # 4. Copia as viagens que o VNS realmente criou
        if k_idx < len(sua_solucao.routes):
            num_viagens_feitas_por_este_onibus = len(sua_solucao.routes[k_idx])
            
            for v_idx, trip_route in enumerate(sua_solucao.routes[k_idx]):
                v_prof = v_idx + 1  # Índice do professor (base 1)
                
                # Copia a rota e os tempos
                solucao_final.rota[k_prof][v_prof] = trip_route
                solucao_final.chegada[k_prof][v_prof] = sua_solucao.times[k_idx][v_idx]

        # 5. Preenche as viagens NÃO UTILIZADAS com listas vazias
        # O loop começa de onde o anterior parou
        for v_idx in range(num_viagens_feitas_por_este_onibus, num_viagens_total):
            v_prof = v_idx + 1
            solucao_final.rota[k_prof][v_prof] = []
            
            # O validador 'factivel' do professor quebra se 'chegada' for []
            # Fornecemos uma lista "dummy" com duração 0.0 para evitar o crash.
            solucao_final.chegada[k_prof][v_prof] = []
            
    return solucao_final

def resolva(dados: Dados, numero_avaliacoes: int) -> SolucaoFinal:
    """
    Executa o algoritmo VNS (Variable Neighborhood Search) para resolver
    o problema de embarque remoto, conforme especificado.
    """
    
    # --- 1. Configurar Parâmetros do VNS ---
    
    pesos_penalidade = {
        'lambda_tw': 1_000_000,
        'lambda_tmax': 10_000,
        'tmax': dados.Tmax
    }
    
    local_search_ops = [
        TwoOpt(base_intensity=1),
        RemoveAndReinsert(base_intensity=1),
        InterTripSwap(base_intensity=1),
    ]
    shake_ops = [
        MergeTrips(base_intensity=3),
        SwapTripsBetweenBuses(base_intensity=4),
        SplitTrip(base_intensity=4),
    ]
    scaling_factor_iters = 0.05

    # --- 2. Construir Solução Inicial ---
    
    seed = random.randint(0, 999_999_999)
    solucao_inicial = VnsSolution(dados.K, dados, pesos_penalidade)
    solucao_inicial.build_initial_solution(seed=seed)

    # --- 3. Configurar e Executar o VNS ---
    
    vns_solver = VariableNeighborhoodSearch(
        local_search_neighborhoods=local_search_ops,
        shake_neighborhoods=shake_ops,
        max_evaluations=numero_avaliacoes,
        scaling_factor=scaling_factor_iters
    )

    melhor_solucao_vns, stats = vns_solver.solve(
        initial_solution=solucao_inicial, 
        quiet=True
    )
    
    # --- 4. Traduzir e Retornar a Solução ---
    
    if not melhor_solucao_vns:
        # Adiciona um log para sabermos se o VNS falhou
        # print("[DEBUG] VNS falhou em retornar uma solução.")
        return SolucaoFinal()

    # Log para nosso 'double-check' interno
    if not melhor_solucao_vns.is_valid:
        # print(f"[DEBUG] VNS está retornando uma solução que ele mesmo considera INVÁLIDA! (Violações: {melhor_solucao_vns.violations})")
        pass
    else:
        # print(f"[DEBUG] VNS retornou uma solução que ele considera VÁLIDA.")
        pass

    solucao_formatada = _traduzir_solucao(melhor_solucao_vns, dados)
    
    return solucao_formatada