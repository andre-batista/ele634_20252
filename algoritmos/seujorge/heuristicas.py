#!/usr/bin/env python3
"""
Módulo de Resolução com Meta-heurística (Algoritmo Genético) para o 
Problema de Embarque Remoto.

(Versão 6 - Final: Correção de viagens vazias para o validador oficial)
"""

import json
import random
import numpy as np
from time import time
from dados import Dados
from solucao import Solucao
from typing import List, Dict, Tuple, Any

class AlgoritmoGenetico:
    """
    Implementa o Algoritmo Genético para o problema de embarque remoto.
    """
    
    def __init__(self, 
                 dados: Dados, 
                 tam_populacao: int, 
                 taxa_crossover: float, 
                 taxa_mutacao: float, 
                 tam_torneio: int = 3,
                 max_avaliacoes: int = 10000):
        """
        Inicializa os parâmetros do Algoritmo Genético.
        """
        self.dados = dados
        self.n_reqs = self.dados.n
        self.tam_populacao = tam_populacao
        self.taxa_crossover = taxa_crossover
        self.taxa_mutacao = taxa_mutacao
        self.tam_torneio = tam_torneio
        
        self.max_avaliacoes = max_avaliacoes
        self.avaliacoes = 0
        
        self.PENALIDADE_JANELA = 10000
        self.PENALIDADE_TMAX = 10000
        self.PENALIDADE_FROTA = 500000

    # --- 1. Funções de População e Cromossomo ---

    def _cria_cromossomo(self) -> List[int]:
        cromossomo = list(range(1, self.n_reqs + 1))
        random.shuffle(cromossomo)
        return cromossomo

    def _cria_populacao_inicial(self) -> List[List[int]]:
        return [self._cria_cromossomo() for _ in range(self.tam_populacao)]

    # --- 2. Função de Avaliação (Fitness) e Decodificação ---
    
    def _avalia_individuo(self, cromo: List[int]) -> Tuple:
        self.avaliacoes += 1
        return self._decodifica_solucao(cromo)

    def _decodifica_solucao(self, cromossomo: List[int]) -> Tuple:
        """
        Decodifica um cromossomo em rotas.
        O tempo de chegada[0] (garagem) é ajustado para refletir o INÍCIO DA PREPARAÇÃO.
        """
        
        rotas: Dict[int, Dict[int, List[int]]] = {k: {} for k in range(1, self.dados.K + 1)}
        chegadas: Dict[int, Dict[int, List[float]]] = {k: {} for k in range(1, self.dados.K + 1)}
        
        custo_total = 0.0
        penalidade = 0.0
        
        # Tempo em que o ônibus k estará pronto PARA SAIR da garagem
        tempo_prontidao_onibus = {k: self.dados.s[0] for k in range(1, self.dados.K + 1)}
        viagens_usadas = {k: 0 for k in range(1, self.dados.K + 1)}
        
        reqs_pendentes = list(cromossomo)
        reqs_nao_alocadas = []

        while reqs_pendentes:
            req = reqs_pendentes.pop(0)
            
            melhor_custo_insercao = float('inf')
            melhor_spot = None 
            
            for k in range(1, self.dados.K + 1):
                
                # --- OPÇÃO 1: Inserir no final da última viagem ---
                v = viagens_usadas[k]
                if v > 0:
                    rota_atual = rotas[k][v]
                    chegada_atual = chegadas[k][v]
                    
                    ultimo_no_rota = rota_atual[-2]
                    tempo_saida_ultimo_no = chegada_atual[-2] + self.dados.s[ultimo_no_rota]
                    
                    tempo_chegada_req = tempo_saida_ultimo_no + self.dados.T[ultimo_no_rota, req]
                    if tempo_chegada_req < self.dados.e[req-1]:
                        tempo_chegada_req = self.dados.e[req-1]
                    
                    tempo_saida_req = tempo_chegada_req + self.dados.s[req]
                    tempo_retorno_garagem = tempo_saida_req + self.dados.T[req, 0]
                    
                    # Duração: Diferença entre retorno e início da PREPARAÇÃO (chegada[0])
                    inicio_prep_viagem = chegada_atual[0]
                    duracao_viagem = tempo_retorno_garagem - inicio_prep_viagem
                    
                    custo_delta = (self.dados.c[ultimo_no_rota, req] + self.dados.c[req, 0]) - self.dados.c[ultimo_no_rota, 0]
                    pen_janela = max(0, tempo_chegada_req - self.dados.l[req-1]) * self.PENALIDADE_JANELA
                    pen_tmax = max(0, duracao_viagem - self.dados.Tmax) * self.PENALIDADE_TMAX
                    
                    custo_total_opcao = custo_delta + pen_janela + pen_tmax
                    
                    if custo_total_opcao < melhor_custo_insercao:
                        melhor_custo_insercao = custo_total_opcao
                        rota_nova = rota_atual[:-1] + [req, 0]
                        chegada_nova = chegada_atual[:-1] + [tempo_chegada_req, tempo_retorno_garagem]
                        melhor_spot = (k, v, 'insert', rota_nova, chegada_nova, custo_delta, pen_janela + pen_tmax)

                # --- OPÇÃO 2: Criar uma nova viagem ---
                if viagens_usadas[k] < self.dados.r:
                    v_novo = viagens_usadas[k] + 1
                    
                    tempo_saida_previsto = tempo_prontidao_onibus[k]
                    tempo_chegada_req = tempo_saida_previsto + self.dados.T[0, req]
                    
                    if tempo_chegada_req < self.dados.e[req-1]:
                        tempo_chegada_req = self.dados.e[req-1]
                    
                    # Recalcula a saída real baseada na janela da requisição
                    tempo_saida_real = tempo_chegada_req - self.dados.T[0, req]
                    
                    # O tempo registrado em chegada[0] deve ser o INÍCIO DA PREPARAÇÃO
                    tempo_inicio_prep = tempo_saida_real - self.dados.s[0]
                    
                    tempo_saida_req = tempo_chegada_req + self.dados.s[req]
                    tempo_retorno_garagem = tempo_saida_req + self.dados.T[req, 0]
                    
                    duracao_viagem = tempo_retorno_garagem - tempo_inicio_prep
                    
                    custo_viagem = self.dados.c[0, req] + self.dados.c[req, 0]
                    pen_janela = max(0, tempo_chegada_req - self.dados.l[req-1]) * self.PENALIDADE_JANELA
                    pen_tmax = max(0, duracao_viagem - self.dados.Tmax) * self.PENALIDADE_TMAX

                    custo_total_opcao = custo_viagem + pen_janela + pen_tmax

                    if custo_total_opcao < melhor_custo_insercao:
                        melhor_custo_insercao = custo_total_opcao
                        rota_nova = [0, req, 0]
                        # Registra [Inicio_Prep, Chegada_Req, Chegada_Garagem]
                        chegada_nova = [tempo_inicio_prep, tempo_chegada_req, tempo_retorno_garagem]
                        melhor_spot = (k, v_novo, 'new', rota_nova, chegada_nova, custo_viagem, pen_janela + pen_tmax)
            
            # Aloca a requisição
            if melhor_spot:
                (k_best, v_best, tipo, r_new, c_new, custo_add, pen_add) = melhor_spot
                
                rotas[k_best][v_best] = r_new
                chegadas[k_best][v_best] = c_new
                custo_total += custo_add
                penalidade += pen_add
                
                tempo_prontidao_onibus[k_best] = c_new[-1] + self.dados.s[0]
                if tipo == 'new':
                    viagens_usadas[k_best] += 1
            else:
                reqs_nao_alocadas.append(req)

        penalidade += len(reqs_nao_alocadas) * self.PENALIDADE_FROTA
        
        fitness = 1.0 / (custo_total + penalidade + 1e-6)
        return fitness, custo_total, penalidade, cromossomo, rotas, chegadas

    # --- 3. Operadores Genéticos ---
    
    def _selecao_torneio(self, populacao_avaliada: List[Tuple]) -> Tuple:
        competidores = random.sample(populacao_avaliada, self.tam_torneio)
        competidores.sort(key=lambda x: x[0], reverse=True) 
        return competidores[0] 

    def _crossover_ox(self, pai1: List[int], pai2: List[int]) -> List[int]:
        n = self.n_reqs
        filho = [None] * n
        p1, p2 = sorted(random.sample(range(n), 2))
        segmento = pai1[p1:p2+1]
        filho[p1:p2+1] = segmento
        idx_filho = (p2 + 1) % n
        idx_pai2 = (p2 + 1) % n
        while filho[idx_filho] is None:
            gene = pai2[idx_pai2]
            if gene not in segmento:
                filho[idx_filho] = gene
                idx_filho = (idx_filho + 1) % n
            idx_pai2 = (idx_pai2 + 1) % n
        return filho

    def _mutacao_swap(self, cromossomo: List[int]) -> List[int]:
        idx1, idx2 = random.sample(range(self.n_reqs), 2)
        cromossomo[idx1], cromossomo[idx2] = cromossomo[idx2], cromossomo[idx1]
        return cromossomo

    # --- 4. Execução do Algoritmo ---

    def executa(self) -> Solucao:
        # print("Iniciando Algoritmo Genético...")
        # print(f"População: {self.tam_populacao}, Max Avaliações: {self.max_avaliacoes}")
        
        populacao = self._cria_populacao_inicial()
        melhor_solucao_global = None
        melhor_solucao_FACTIVEL = None
        
        self.avaliacoes = 0
        
        while self.avaliacoes < self.max_avaliacoes:
            pop_avaliada = []
            for cromo in populacao:
                if self.avaliacoes >= self.max_avaliacoes:
                    break
                pop_avaliada.append(self._avalia_individuo(cromo))
            
            if not pop_avaliada:
                break 

            pop_avaliada.sort(key=lambda x: x[0], reverse=True)
            melhor_geracao = pop_avaliada[0]
            
            if melhor_solucao_global is None or melhor_geracao[0] > melhor_solucao_global[0]:
                melhor_solucao_global = melhor_geracao
            
            for ind in pop_avaliada:
                if ind[2] == 0: # Penalidade 0
                    if melhor_solucao_FACTIVEL is None:
                        melhor_solucao_FACTIVEL = ind
                    elif ind[1] < melhor_solucao_FACTIVEL[1]:
                        melhor_solucao_FACTIVEL = ind

            # Elitismo e Nova População
            nova_populacao = [melhor_geracao[3]] 
            while len(nova_populacao) < self.tam_populacao:
                pai1 = self._selecao_torneio(pop_avaliada)[3]
                pai2 = self._selecao_torneio(pop_avaliada)[3]
                
                filho = self._crossover_ox(pai1, pai2) if random.random() < self.taxa_crossover else pai1[:]
                if random.random() < self.taxa_mutacao:
                    filho = self._mutacao_swap(filho)
                nova_populacao.append(filho)
            
            populacao = nova_populacao

        if melhor_solucao_FACTIVEL is not None:
            return self._converte_para_objeto_solucao(melhor_solucao_FACTIVEL)
        else:
            return self._converte_para_objeto_solucao(melhor_solucao_global) if melhor_solucao_global else Solucao()

    def _converte_para_objeto_solucao(self, melhor_individuo: Tuple) -> Solucao:
        fitness, custo, penalidade, cromo, rotas, chegadas = melhor_individuo
        sol = Solucao()
        sol.fx = custo + penalidade

        K_range = range(1, self.dados.K + 1)
        V_range = range(1, self.dados.r + 1)

        sol.rota = {k: {} for k in K_range}
        sol.chegada = {k: {} for k in K_range}

        for k in K_range:
            for v in V_range:
                # CORREÇÃO CRÍTICA:
                # Só adiciona no dicionário se a viagem realmente existir (não for vazia).
                # Isso impede que o validador 'factivel' tente ler listas vazias.
                if k in rotas and v in rotas[k] and len(rotas[k][v]) > 0:
                    sol.rota[k][v] = rotas[k][v]
                    sol.chegada[k][v] = chegadas[k][v]
                # Se não existir, NÃO adiciona chaves vazias ou listas vazias.
                # O método factivel() do professor usa "if v not in self.rota[k]: continue",
                # então ele vai pular corretamente essas viagens.

        return sol
