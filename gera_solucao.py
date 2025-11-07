"""
Script para Geração de Solução Heurística - Problema de Embarque Remoto

Este script implementa uma heurística construtiva gulosa para o problema de 
roteamento de ônibus em aeroportos com embarque remoto. A estratégia utilizada 
é Earliest Deadline First (EDF), atendendo requisições em ordem crescente de deadline.

Características:
- Ordenação: Por deadline das requisições
- Inserção: Primeira posição factível encontrada
- Validação: Respeita janelas de tempo e autonomia máxima

Uso:
    python gera_solucao.py

Autor: André Batista
Data: Setembro 2025
"""

import numpy as np
from dados import carrega_dados_json
from solucao import Solucao
from exato import Exato


# ==============================================================================
# CONFIGURAÇÃO E CARREGAMENTO DE DADOS
# ==============================================================================

print("=" * 70)
print("GERADOR DE SOLUÇÃO HEURÍSTICA - PROBLEMA DE EMBARQUE REMOTO")
print("=" * 70)

# Carrega instância do problema
ARQUIVO_INSTANCIA = "./dados/grande.json"
print(f"\nCarregando instância: {ARQUIVO_INSTANCIA}")
dados = carrega_dados_json(ARQUIVO_INSTANCIA)
print(f"✓ Instância carregada: {dados.n} requisições, {dados.K} ônibus, {dados.r} viagens/ônibus")


# ==============================================================================
# INICIALIZAÇÃO DA SOLUÇÃO
# ==============================================================================

print("\n" + "-" * 70)
print("GERANDO SOLUÇÃO HEURÍSTICA (Earliest Deadline First)")
print("-" * 70)

# Cria estrutura da solução
solucao = Solucao()

# Define conjuntos de índices
K = range(1, dados.K + 1)  # Ônibus
V = range(1, dados.r + 1)  # Viagens

# Inicializa estruturas de rotas e chegadas
for k in K:
    solucao.rota[k] = {}
    solucao.chegada[k] = {}
    for v in V:
        solucao.rota[k][v] = []
        solucao.chegada[k][v] = []

# Ordena requisições por deadline (Earliest Deadline First)
ordem_requisicoes = np.argsort(dados.l) + 1
print(f"✓ Requisições ordenadas por deadline (EDF)")

# Contador de requisições não atendidas
requisicoes_nao_atendidas = dados.n


# ==============================================================================
# CONSTRUÇÃO DA SOLUÇÃO HEURÍSTICA
# ==============================================================================

# Itera sobre cada ônibus da frota
for k in K:
    tempo_atual = 0  # Tempo atual do ônibus k
    
    # Itera sobre cada viagem possível do ônibus k
    for v in V:
        # Inicializa variáveis da viagem
        rota = [0]  # Inicia na garagem
        chegada = []
        contador_requisicoes = 0
        duracao_viagem = 0
        continuar_insercao = True
        viagem_tem_requisicoes = False
        
        # Tenta inserir requisições na rota enquanto for factível
        while continuar_insercao:
            # Calcula tempo de viagem até cada requisição disponível
            tempo_ate_requisicao = dados.s[rota[-1]] + dados.T[rota[-1], ordem_requisicoes]
            
            # Calcula tempo de chegada em cada requisição (respeitando earliest time)
            chegada_na_requisicao = np.zeros(len(ordem_requisicoes))
            for j in range(len(ordem_requisicoes)):
                req_id = ordem_requisicoes[j]
                chegada_sem_espera = tempo_atual + tempo_ate_requisicao[j]
                # Respeita earliest arrival time
                chegada_na_requisicao[j] = max(chegada_sem_espera, dados.e[req_id - 1])
            
            # Calcula duração total se incluir cada requisição e voltar para garagem
            duracao_com_volta = np.zeros(len(ordem_requisicoes))
            for j in range(len(ordem_requisicoes)):
                req_id = ordem_requisicoes[j]
                
                if contador_requisicoes > 0:
                    # Já tem requisições na rota
                    intervalo = chegada_na_requisicao[j] - tempo_atual
                    duracao_com_volta[j] = (duracao_viagem + intervalo + 
                                           dados.s[req_id] + dados.T[req_id, 0])
                else:
                    # Primeira requisição da viagem
                    duracao_com_volta[j] = (tempo_ate_requisicao[j] + 
                                           dados.s[req_id] + dados.T[req_id, 0])
            
            # Tenta inserir a primeira requisição factível encontrada
            requisicao_inserida = False
            
            for j in range(len(ordem_requisicoes)):
                req_id = ordem_requisicoes[j]
                
                # Verifica factibilidade: deadline e autonomia
                respeita_deadline = chegada_na_requisicao[j] <= dados.l[req_id - 1]
                respeita_autonomia = duracao_com_volta[j] <= dados.Tmax
                
                if respeita_deadline and respeita_autonomia:
                    # Requisição é factível - insere na rota
                    rota.append(int(req_id))
                    tempo_chegada = float(chegada_na_requisicao[j])
                    
                    # Primeira requisição: adiciona tempo de saída da garagem
                    if contador_requisicoes == 0:
                        tempo_saida_garagem = tempo_chegada - tempo_ate_requisicao[j]
                        chegada.append(float(tempo_saida_garagem))
                    
                    # Adiciona tempo de chegada na requisição
                    chegada.append(tempo_chegada)
                    duracao_viagem = float(chegada[-1] - chegada[0])
                    
                    # Remove requisição da lista de disponíveis
                    ordem_requisicoes = np.delete(ordem_requisicoes, j)
                    
                    # Atualiza contadores
                    contador_requisicoes += 1
                    tempo_atual = tempo_chegada
                    viagem_tem_requisicoes = True
                    requisicoes_nao_atendidas -= 1
                    requisicao_inserida = True
                    break
                
                # Última requisição disponível e não é factível
                elif j == ordem_requisicoes.size - 1:
                    if viagem_tem_requisicoes:
                        # Finaliza viagem retornando à garagem
                        continuar_insercao = False
                        rota.append(0)
                        tempo_atual += dados.s[rota[-2]] + dados.T[rota[-2], 0]
                        chegada.append(float(tempo_atual))
                        duracao_viagem = float(chegada[-1] - chegada[0])
                    else:
                        # Nenhuma requisição factível - viagem vazia
                        continuar_insercao = False
            
            # Verifica se todas as requisições foram atendidas
            if requisicoes_nao_atendidas == 0:
                if requisicao_inserida:
                    # Finaliza viagem retornando à garagem
                    tempo_atual += dados.T[rota[-1], 0] + dados.s[rota[-1]]
                    rota.append(0)
                    chegada.append(float(tempo_atual))
                break
        
        # Armazena viagem na solução se atendeu alguma requisição
        if viagem_tem_requisicoes:
            solucao.rota[k][v] = rota
            solucao.chegada[k][v] = chegada
            n_req = len([r for r in rota if r != 0])
            print(f"  Ônibus {k}, Viagem {v}: {n_req} requisições atendidas")
        
        # Para de criar viagens se todas requisições foram atendidas
        if requisicoes_nao_atendidas == 0:
            break
    
    # Para de usar ônibus se todas requisições foram atendidas
    if requisicoes_nao_atendidas == 0:
        break


# ==============================================================================
# EXIBIÇÃO DA SOLUÇÃO HEURÍSTICA
# ==============================================================================

print("\n" + "-" * 70)
print("SOLUÇÃO HEURÍSTICA GERADA")
print("-" * 70)
print(solucao)

requisicoes_atendidas = dados.n - requisicoes_nao_atendidas
taxa_atendimento = (requisicoes_atendidas / dados.n) * 100

print(f"\nRequisições atendidas: {requisicoes_atendidas}/{dados.n} ({taxa_atendimento:.1f}%)")

if requisicoes_nao_atendidas > 0:
    print(f"⚠ ATENÇÃO: {requisicoes_nao_atendidas} requisições não foram atendidas!")


# ==============================================================================
# RESOLUÇÃO COM MÉTODO EXATO (OPCIONAL)
# ==============================================================================

print("\n" + "=" * 70)
resposta = input("Deseja resolver com método exato usando esta solução como warm start? (s/n): ")

if resposta.lower() == 's':
    print("\n" + "-" * 70)
    print("RESOLVENDO COM MÉTODO EXATO")
    print("-" * 70)
    
    metodo = Exato(limite_tempo=12*3600)
    solucao_otima = metodo.resolve(dados, solucao_inicial=solucao)
    
    print("\n" + "-" * 70)
    print("SOLUÇÃO ÓTIMA")
    print("-" * 70)
    print(solucao_otima)
    
    if solucao.fx and solucao_otima.fx:
        gap = ((solucao.fx - solucao_otima.fx) / solucao_otima.fx) * 100
        print(f"\nGap entre heurística e ótimo: {gap:.2f}%")
    
    solucao_otima.salvar("otimo_grande.json")

print("\n" + "=" * 70)
print("EXECUÇÃO CONCLUÍDA")
print("=" * 70)