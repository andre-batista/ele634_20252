"""
Ponto de Entrada Principal para Resolução com Meta-heurística (Algoritmo Genético).

Este arquivo contém a interface padronizada `resolva` exigida pelas
orientações do trabalho, que será utilizada para a correção automática.

Ele importa a implementação do Algoritmo Genético (ga_aeroporto.py) e 
as classes de dados (dados.py, solucao.py).

Nas linhas 69 a 92, você pode indicar o arquivo de instâncias que deseja testar: variável dados_teste

Nas linhas 94 a 106, você pode ajustar o número de avaliações para o teste local: constante MAX_AVALIACOES_TESTE

"""

from dados import Dados
from solucao import Solucao
from heuristicas import AlgoritmoGenetico
from time import time

def resolva(dados: Dados, numero_avaliacoes: int) -> Solucao:
    """
    Executa o Algoritmo Genético respeitando o número de avaliações.
    Retorna um objeto `Solucao` conforme as orientações.
    
    Args:
        dados (Dados): Objeto com os dados da instância.
        numero_avaliacoes (int): Orçamento total de avaliações da função objetivo.
    
    Returns:
        Solucao: A melhor solução encontrada pelo AG.
    """
    print(f"Iniciando GA com orçamento de {numero_avaliacoes} avaliações...")
    
    # --- Hiperparâmetros do Algoritmo Genético ---
    # Como calibrar esses valores?
    tam_pop = 100  # Para cada 100 indivíduos da população, o AG chamará _decodifica_solucao(cromo). Isso conta como uma avaliação.
    taxa_crossover = 0.85
    taxa_mutacao = 0.15 # Aumentei um pouco a mutação para instâncias maiores
    tam_torneio = 3
    # -------------------------------------------------

    tic = time()
    
    # Instancia o GA com o orçamento de avaliações recebido
    ga = AlgoritmoGenetico(
        dados=dados,
        tam_populacao=tam_pop,
        taxa_crossover=taxa_crossover,
        taxa_mutacao=taxa_mutacao,
        tam_torneio=tam_torneio,
        max_avaliacoes=numero_avaliacoes # Critério de parada
    )

    # Executa o algoritmo
    sol = ga.executa()
    
    tempo_total = time() - tic
    print(f"...GA concluído em {tempo_total:.2f}s. Avaliações usadas: {ga.avaliacoes}")
    
    return sol

# --- Bloco de Teste Opcional ---
# Este bloco NÃO será usado pelo professor, mas serve para você testar
# este arquivo diretamente, simulando a chamada do professor.
if __name__ == "__main__":
    from dados import carrega_dados_json
    
    try:
        # Tenta carregar a instância pequena
        dados_teste = carrega_dados_json('./dados/pequena.json')
        print("Teste local: Carregando 'pequena.json'")

        # Tenta carregar a instância média
        #dados_teste = carrega_dados_json('./dados/media.json')
        #print("Teste local: Carregando 'media.json'")

        # Tenta carregar a instância grande
        #dados_teste = carrega_dados_json('./dados/grande.json')
        #print("Teste local: Carregando 'grande.json'")

        # Tenta carregar a instância rush
        #dados_teste = carrega_dados_json('./dados/rush.json')
        #print("Teste local: Carregando 'rush.json'")
    except FileNotFoundError:
        try:
            # Se falhar, carrega a pequena
            dados_teste = carrega_dados_json('./dados/pequena.json')
            print("Teste local: Carregando 'pequena.json'")
        except FileNotFoundError:
            print("Erro: Nenhum arquivo de dados (.json) encontrado na pasta ./dados/")
            exit()

    # Define um número de avaliações para o teste
    # Pequena
    MAX_AVALIACOES_TESTE = 2100

    # Media
    #MAX_AVALIACOES_TESTE = 48240

    # Grande
    #MAX_AVALIACOES_TESTE = 118800
    
    # Rush
    #MAX_AVALIACOES_TESTE = 118800

    # Chama a função principal de resolução
    solucao_final = resolva(dados_teste, MAX_AVALIACOES_TESTE)

    # Exibe os resultados
    print("\n" + "="*50)
    print(f"MELHOR SOLUÇÃO ENCONTRADA (Teste Local)")
    print(f"Custo total (com penalidades): {solucao_final.fx:.2f}")
    print("="*50)
    print(solucao_final)

    print("\n" + "="*50)
    print(f"DETALHE DAS VIAGENS (Validação)")
    print("="*50)

    try:
        # Pega as penalidades do __init__ da classe para referência
        pen_janela = ga.PENALIDADE_JANELA
        pen_tmax = ga.PENALIDADE_TMAX
    except NameError:
        # Se 'ga' não estiver disponível, define valores padrão
        pen_janela = 10000 
        pen_tmax = 10000

    custo_verificado = 0.0
    penalidade_verificada = 0.0

    for k in solucao_final.rota:
        for v in solucao_final.rota[k]:
            rota = solucao_final.rota[k][v]
            chegadas = solucao_final.chegada[k][v]
            
            # Pula viagens não utilizadas
            if len(rota) <= 2: 
                continue 
                
            print(f"--- Ônibus {k}, Viagem {v} ---")
            print(f"  Rota:    {rota}")
            print(f"  Chegada: {[round(t, 2) for t in chegadas]}")
            
            # 1. Validação do Custo da Rota
            custo_viagem = 0.0
            for i in range(len(rota) - 1):
                no_origem = rota[i]
                no_destino = rota[i+1]
                custo_viagem += dados_teste.c[no_origem, no_destino]
            
            custo_verificado += custo_viagem
            print(f"  Custo da Viagem: {custo_viagem:.2f}")

            # 2. Validação do Tmax (Duração da Viagem)
            tempo_saida_garagem = chegadas[0]
            tempo_retorno_garagem = chegadas[-1]
            duracao = tempo_retorno_garagem - tempo_saida_garagem
            print(f"  Duração: {duracao:.2f} (Limite Tmax={dados_teste.Tmax})")
            
            if duracao > dados_teste.Tmax:
                p = (duracao - dados_teste.Tmax) * pen_tmax
                penalidade_verificada += p
                print(f"  [VIOLAÇÃO TMAX! Pen: {p:.2f}]")

            # 3. Validação das Janelas de Tempo (para cada req na rota)
            for i in range(1, len(rota) - 1): # Pula a garagem (início e fim)
                req = rota[i]
                if req == 0:
                    continue
                chegada_req = chegadas[i]
                janela_e = dados_teste.e[req-1]
                janela_l = dados_teste.l[req-1]
                
                print(f"    Req {req}: Chegada={chegada_req:.2f} (Janela=[{janela_e}, {janela_l}])")
                
                if chegada_req > janela_l:
                    p = (chegada_req - janela_l) * pen_janela
                    penalidade_verificada += p
                    print(f"    [VIOLAÇÃO JANELA! Pen: {p:.2f}]")
    
    print("\n" + "="*50)
    print("VERIFICAÇÃO FEITA PELO GRUPO")
    print("\n" + "="*50)
    print(f"\nCusto (da Solução):   {solucao_final.fx:.2f}")
    print(f"Custo (Verificado):   {custo_verificado:.2f}")
    print(f"Penalidade (Verificada): {penalidade_verificada:.2f}")
    
    if abs(solucao_final.fx - (custo_verificado + penalidade_verificada)) < 0.01:
        print(">> SUCESSO: O custo da solução bate com a verificação!")
    else:
        print(">> ERRO: O custo da solução está DIFERENTE da verificação.")
    
    print("\n" + "="*50)
    print("VALIDAÇÃO OFICIAL DO PROFESSOR")
    print("="*50)
    
    # Chama o método oficial do professor
    e_factivel = solucao_final.factivel(dados_teste, verbose=True)
    
    if e_factivel:
        print("\n>>> SUCESSO TOTAL: A solução foi aprovada pelo validador oficial!")
    else:
        print("\n>>> PERIGO: A solução foi rejeitada pelo validador oficial.")