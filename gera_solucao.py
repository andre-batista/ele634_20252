from dados import Dados, carrega_dados_json
from solucao import Solucao
import numpy as np

dados = carrega_dados_json("./dados/media.json")
solucao = Solucao()

ordem_requisicoes = np.argsort(dados.l) + 1

K = range(1, dados.K + 1)
V = range(1, dados.r + 1)

for k in K:
    
    solucao.rota[k] = {}
    solucao.chegada[k] = {}
    
    for v in V:
        solucao.rota[k][v] = []
        solucao.chegada[k][v] = []

numero_requisicoes_nao_atendidas = dados.n

for k in K:

    t = 0

    for v in V:
        
        rota = [0]
        chegada = []
        i = 0
        duracao_viagem = 0
        cabe_mais_requisicoes = True
        uma_requisicao_foi_atendida = False

        while cabe_mais_requisicoes:

            tempo_ate_requisicao = dados.s[rota[-1]] + dados.T[rota[-1], ordem_requisicoes]
            chegada_na_requisicao = t + tempo_ate_requisicao
            duracao_de_viagem_em_caso_de_volta_para_garagem = duracao_viagem + tempo_ate_requisicao + dados.s[ordem_requisicoes] + dados.T[ordem_requisicoes, 0]
            for j in range(len(duracao_de_viagem_em_caso_de_volta_para_garagem)):
                if t + tempo_ate_requisicao[j] <= dados.e[ordem_requisicoes[j]-1] and i != 0:
                    duracao_de_viagem_em_caso_de_volta_para_garagem[j] = duracao_viagem + (dados.e[ordem_requisicoes[j]-1] - t) + dados.s[ordem_requisicoes[j]] + dados.T[ordem_requisicoes[j], 0]


            # Eu tenho que escolher uma requisição que:
            # 1. Ainda não foi atendida
            # 2. O instante atual t não ultrapassa o fim da janela de tempo da requisição
            # 3. A duração da viagem até essa requisição mais o tempo para voltar para a garagem não ultrapassa Tmax
            for j in range(len(ordem_requisicoes)):

                if ((chegada_na_requisicao[j] <= dados.l[ordem_requisicoes[j]-1]) 
                    and (duracao_de_viagem_em_caso_de_volta_para_garagem[j] 
                         <= dados.Tmax)):

                    rota.append(int(ordem_requisicoes[j]))
                    # O tempo de chegada na nova requisição é ou o tempo de chegada ou o início da janela de tempo, o que for maior
                    chegada_oficial = float(max(chegada_na_requisicao[j], dados.e[ordem_requisicoes[j]-1]))
                    
                    if i == 0:
                        chegada.append(float(chegada_oficial - tempo_ate_requisicao[j]))

                    chegada.append(chegada_oficial)
                    duracao_viagem = float(chegada[-1] - chegada[0])
                    ordem_requisicoes = np.delete(ordem_requisicoes, j)
                    i += 1
                    t = chegada[-1]
                    uma_requisicao_foi_atendida = True
                    numero_requisicoes_nao_atendidas -= 1
                    break
                elif j == ordem_requisicoes.size - 1 and uma_requisicao_foi_atendida:
                    cabe_mais_requisicoes = False
                    rota.append(0)
                    t += dados.T[rota[-1], 0] + dados.s[rota[-1]]
                    chegada.append(float(t))
                elif j == ordem_requisicoes.size - 1 and not uma_requisicao_foi_atendida:
                    cabe_mais_requisicoes = False
        
            if numero_requisicoes_nao_atendidas == 0:
                t += dados.T[rota[-1], 0] + dados.s[rota[-1]]
                rota.append(0)
                chegada.append(float(t))
                break
        
        if uma_requisicao_foi_atendida:
            solucao.rota[k][v] = rota
            solucao.chegada[k][v] = chegada

        if numero_requisicoes_nao_atendidas == 0:
            break
    if numero_requisicoes_nao_atendidas == 0:
        break
        
print(solucao)
from exato import Exato

metodo = Exato()
solucao_otima = metodo.resolve(dados, solucao_inicial=solucao)
print("Solução ótima:")
print(solucao_otima)