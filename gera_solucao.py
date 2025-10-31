from dados import Dados, carrega_dados_json
from solucao import Solucao
import numpy as np

dados = carrega_dados_json("./dados/pequena.json")
solucao = Solucao()

ordem_requisicoes = np.argsort(dados.l) + 1

K = range(1, dados.K + 1)
V = range(1, dados.r + 1)

for k in K:

    t = 0

    for v in V:
        
        rota = [0]
        i = 0
        duracao_viagem = 0
        cabe_mais_requisicoes = True

        while cabe_mais_requisicoes:

            tempo_ate_requisicao = dados.s[rota[-1]] + dados.T[rota[-1], ordem_requisicoes]
            chegada_na_requisicao = t + tempo_ate_requisicao
            duracao_de_viagem_em_caso_de_volta_para_garagem = duracao_viagem + tempo_ate_requisicao + dados.s[ordem_requisicoes] + dados.T[ordem_requisicoes, 0]

            # Eu tenho que escolher uma requisição que:
            # 1. Ainda não foi atendida
            # 2. O instante atual t não ultrapassa o fim da janela de tempo da requisição
            # 3. A duração da viagem até essa requisição mais o tempo para voltar para a garagem não ultrapassa Tmax
            exit()