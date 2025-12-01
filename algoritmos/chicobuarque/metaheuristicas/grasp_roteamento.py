import numpy as np
import matplotlib.pyplot as plt
import random
import time
from typing import List, Tuple, Dict
from andre_repositorio.utils import carregar_instancia as andre_carregar_instancia

# Define seed for reproducibility
np.random.seed(42)
random.seed(42)

# ============================================================================
# FUNÇÕES PARA O PROBLEMA DE ROTEAMENTO DE ÔNIBUS
# ============================================================================

def carregar_instancia(tipoInstancia = 'pequena'):
    """
    Carrega uma instância do problema de roteamento de ônibus.

    Returns:
        dict: Dicionário com todos os dados da instância
    """
    print("=" * 70)
    print("Gerando instância do problema de roteamento de ônibus...")
    print("=" * 70)

    # instancia = gerar_instancia_aeroporto(
    #     n_voos=n_voos,
    #     capacidade_onibus=50,
    #     n_onibus=n_onibus,
    #     duracao_operacao_horas=duracao_horas,
    #     seed=42
    # )

    arquivo = f'./andre_repositorio/dados/{tipoInstancia}.json'
    instancia = andre_carregar_instancia(arquivo)

    # Extrair dados importantes
    n_req = instancia['numeroRequisicoes']
    n_veic = instancia['numeroOnibus']

    print("=" * 70)
    print(f"Requisições: {n_req}")
    print(f"Ônibus disponíveis: {n_veic}")
    print(f"Máximo viagens por ônibus: {instancia['numeroMaximoViagens']}")
    print(f"Tempo máximo por viagem: {instancia['tempoMaximoViagem']:.1f} min")
    print("=" * 70)

    return instancia


def greedy_randomized_construction(instancia: dict, alpha: float = 0.3) -> List[List[int]]:
    """
    Constrói uma solução GRASP ordenando as requisições pelo início da janela.
    Cada ponto é atribuído ao ônibus mais próximo que consiga atendê-lo.
    Ociosidade é zero (só pode esperar na garagem).

    Args:
        instancia: dicionário com dados da instância
        alpha: fator de aleatoriedade (0 <= alpha <= 1)
    Returns:
        rotas: lista de rotas por ônibus (cada uma iniciando e terminando no depósito)
    """
    # --- Extração dos dados da instância ---
    n_req = instancia['numeroRequisicoes']
    n_veic = instancia['numeroOnibus']
    max_viagens = instancia['numeroMaximoViagens']
    D = np.array(instancia['distanciaRequisicoes'])
    T = np.array(instancia['tempoRequisicoes'])
    s = np.array(instancia['tempoServico'])
    e = np.array(instancia['inicioJanela'])
    l = np.array(instancia['fimJanela'])
    Tmax = instancia['tempoMaximoViagem']
    viagem_time = [0.0 for _ in range(n_veic)]
    depot = 0

    # --- Estado inicial ---
    unvisited = set(range(n_req+1)) - {depot}
    rotas = [[depot] for _ in range(n_veic)]
    current_city = [depot for _ in range(n_veic)]
    times = [0.0 for _ in range(n_veic)]
    viagens_count = [0 for _ in range(n_veic)]

    # --- Ordena pontos pela janela ---
    ordered_points = sorted(list(unvisited), key=lambda i: e[i-1])

    print("\n=== Iniciando construção gulosa temporal ===")
    for ponto in ordered_points:
        print(f"\n📍 Avaliando ponto {ponto} (janela {e[ponto-1]}–{l[ponto-1]})")

        candidatos = []

        # --- Avalia todos os ônibus
        for bus in range(n_veic):
            if viagens_count[bus] >= max_viagens:
                continue
            # Calcula hora de chegada
            arrival = times[bus] + T[current_city[bus], ponto]

            # Se ônibus está na garagem → pode ajustar para início da janela
            if current_city[bus] == depot:
                if arrival < e[ponto-1]:
                    arrival = e[ponto-1]  # espera na garagem
                viagem_time[bus] = 0.0  # reinicia contagem da nova viagem

            # Se chegaria antes da janela, mas não está na garagem → volta para garagem
            elif arrival < e[ponto-1]:
                print(f"⏱️ Ônibus {bus} chegaria antes da janela do ponto {ponto}, voltando para a garagem")
                rotas[bus].append(depot)
                viagens_count[bus] += 1
                current_city[bus] = depot
                times[bus] = 0.0
                viagem_time[bus] = 0.0
                arrival = e[ponto-1]  # agora ele sai da garagem e chega no início da janela

            start_service = arrival
            finish_time = start_service + s[ponto]

            # Verifica se é viável em relação à Tmax e janela
            if viagem_time[bus] + T[current_city[bus], ponto] + s[ponto] + T[ponto, depot] <= Tmax and e[ponto-1] <= arrival <= l[ponto-1]:
                # ✅ ônibus pode atender
                cost = D[current_city[bus], ponto]
                candidatos.append((bus, cost, finish_time))
                print(f"  ✅ Viável: ônibus {bus} (chegada {arrival:.2f}, término {finish_time:.2f}, {cost:.2f})")
            else:
                print(f"  ❌ Inviável: ônibus {bus} (chegada {arrival:.2f}, término {finish_time:.2f}, {cost:.2f})")

        if not candidatos:
            print(f"⚠️ Nenhum ônibus pode atender o ponto {ponto}")
            continue

        # --- Escolhe ônibus (GRASP) ---
        # Prioriza ônibus fora da garagem, depois menor custo
        candidatos.sort(key=lambda x: (
            current_city[x[0]] == depot,  # False (fora da garagem) vem antes de True (na garagem)
            x[1]                          # custo
        ))

        rcl_size = max(1, int(alpha * len(candidatos)))
        bus, cost, finish_time = random.choice(candidatos[:rcl_size])

        # --- Atualiza estado ---
        rotas[bus].append(ponto)
        current_city[bus] = ponto
        times[bus] = finish_time
        unvisited.remove(ponto)

        print(f"➡️ Atribuído: ponto {ponto} → ônibus {bus} (novo tempo {times[bus]:.2f})")

        # Verifica Tmax
        if times[bus] + T[ponto, depot] > Tmax:
            print(f"⏱️ Ônibus {bus} atingiu Tmax, retornando à garagem.")
            rotas[bus].append(depot)
            viagens_count[bus] += 1
            current_city[bus] = depot
            times[bus] = 0.0

    # Fecha viagens pendentes
    for bus in range(n_veic):
        if rotas[bus][-1] != depot:
            rotas[bus].append(depot)
            viagens_count[bus] += 1

    print("\n=== Rotas finais ===")
    for i, r in enumerate(rotas):
        print(f"Ônibus {i}: {r}")

    if unvisited:
        print(f"\n⚠️ Pontos não atendidos: {sorted(list(unvisited))}")
    else:
        print("\n✅ Todas as requisições foram atendidas.")

    return rotas
    """
    Algoritmo GRASP para o Problema de Roteamento de Ônibus.

    Args:
        instancia: Dados da instância
        max_iterations: Número máximo de iterações
        alpha: Parâmetro de aleatoriedade na fase construtiva

    Returns:
        Tuple contendo a melhor solução, seu custo e histórico
    """
    best_solution = None
    best_distance = float('inf')
    iteration_costs = []

    for iteration in range(max_iterations):
        # Fase 1: Construção gulosa aleatorizada
        solution = greedy_randomized_construction(instancia, alpha)

        # Fase 2: Busca local
        solution = local_search(solution, instancia)

        # Avaliar a solução
        distance, max_time, viavel = evaluate_solution(solution, instancia)
        iteration_costs.append(distance)

        # Atualizar a melhor solução (aceitar mesmo se não viável se não temos nenhuma)
        if distance < best_distance:
            if viavel or best_solution is None:
                best_solution = [r.copy() for r in solution]
                best_distance = distance
                status = "viável" if viavel else "inviável"
                print(f"Iteração {iteration+1}: Nova melhor solução ({status}, distância={best_distance:.2f}m, tempo={max_time:.2f}min)")

    return best_solution, best_distance, iteration_costs





# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    # Carregar instância
    instancia = carregar_instancia(tipoInstancia='pequena') #pequena, media, grande, rush

    # Executar GRASP
    print("\nExecutando GRASP para roteamento de ônibus...")
    start_time = time.time()

    first_solution = greedy_randomized_construction(instancia, alpha=0.3)

    execution_time = time.time() - start_time

    # Imprimir solução
    print(f"\nTempo de execução: {execution_time:.2f} segundos")

    # Plotar convergência
    # plt.figure(figsize=(10, 6))
    # plt.plot(range(1, len(iteration_costs) + 1), iteration_costs, marker='o')
    # plt.axhline(y=best_distance, color='r', linestyle='--',
    #             label=f'Melhor solução: {best_distance:.2f}m')
    plt.title("Convergência do GRASP - Problema de Roteamento de Ônibus")
    plt.xlabel("Iteração")
    plt.ylabel("Distância Total (metros)")
    #plt.legend()
    #plt.grid(True)
    #plt.show()