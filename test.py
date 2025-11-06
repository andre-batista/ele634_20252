import numpy as np
from dados import carrega_dados_json
from solucao import Solucao

ARQUIVO_INSTANCIA = "./dados/pequena.json"
ARQUIVO_SOLUCAO = "./dados/otimo_pequena.json"
dados = carrega_dados_json(ARQUIVO_INSTANCIA)
solucao = Solucao()
solucao.carregar(ARQUIVO_SOLUCAO)

K = range(1, dados.K + 1)
V = range(1, dados.r + 1)
N = list(range(1, dados.n + 1))

for k in K:
    for v in V:
        
        if v not in solucao.rota[k]:
            continue
        
        requisicoes = solucao.rota[k][v]
        chegadas = solucao.chegada[k][v]
        
        for i in range(1, len(requisicoes)):
            
            if chegadas[i-1] + dados.s[requisicoes[i-1]] + dados.T[requisicoes[i-1], requisicoes[i]] > chegadas[i] + 1e-4:
                print(f"Inconsistência de tempo: veículo {k}, viagem {v}, de requisição {requisicoes[i-1]} para {requisicoes[i]}")
        
        requisicoes = solucao.rota[k][v][1:-1]
        chegadas = solucao.chegada[k][v][1:-1]

        duracao = solucao.chegada[k][v][-1] - solucao.chegada[k][v][0]
        
        if duracao > dados.Tmax + 1e-4:
            print(f"Veículo {k} na viagem {v} excedeu o tempo máximo: {duracao} > {dados.Tmax}")
        
        for i in range(len(requisicoes)):
            requisicao = requisicoes[i]
            chegada = chegadas[i]
            if chegada < dados.e[requisicao-1]-2e-4 or chegada > dados.l[requisicao-1] + 2e-4:
                print(f"Requisição {requisicao} violou janela de tempo: chegada={chegada}, janela=[{dados.e[requisicao-1]}, {dados.l[requisicao-1]}]")
    
        for requisicao in requisicoes:
            N.remove(requisicao)  
            
if len(N) == 0:
    print("Todas as requisições foram atendidas na solução.")
else:
    print("As seguintes requisições não foram atendidas na solução:", N)