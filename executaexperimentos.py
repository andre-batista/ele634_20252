import sys
import os
from dados import carrega_dados_json
import joblib

sys.path.insert(1, './algoritmos/alcione')
sys.path.insert(1, './algoritmos/cartola')
sys.path.insert(1, './algoritmos/chicobuarque')
sys.path.insert(1, './algoritmos/djavan')
sys.path.insert(1, './algoritmos/seujorge')

from algoritmos.alcione.alcione import resolva as resolva_alcione
from algoritmos.cartola.cartola import resolva as resolva_cartola
from algoritmos.chicobuarque.chicobuarque import resolva as resolva_chicobuarque
from algoritmos.djavan.djavan import resolva as resolva_djavan
from algoritmos.seujorge.seujorge import resolva as resolva_seujorge
    
# Carrega instância do problema
instancia = 'grande'  # Opções: 'pequena', 'media', 'grande', 'rush'
num_avaliacoes = 118800 # 2100, 48240, 118800, 118800
num_execucoes = 30
grupos = ["alcione"]

dados = carrega_dados_json(f'./dados/{instancia}.json')

for grupo in grupos:

    print(f'Executando grupo: {grupo}')

    os.makedirs(f'./resultados/{instancia}/{grupo}', exist_ok=True)

    def executar_algoritmo(execucao, grupo, dados, num_avaliacoes, instancia):
        if grupo == "alcione":
            solucao = resolva_alcione(dados, numero_avaliacoes=num_avaliacoes)
        elif grupo == "cartola":
            solucao = resolva_cartola(dados, numero_avaliacoes=num_avaliacoes)
        elif grupo == "chicobuarque":
            solucao = resolva_chicobuarque(dados, 
                                           numero_avaliacoes=num_avaliacoes)
        elif grupo == "djavan":
            solucao = resolva_djavan(dados, numero_avaliacoes=num_avaliacoes)
        elif grupo == "seujorge":
            solucao = resolva_seujorge(dados, numero_avaliacoes=num_avaliacoes)
        
        solucao.salvar("./resultados/{}/{}/s{}.json".format(instancia, grupo, 
                                                            execucao + 1))
        return solucao
    
    joblib.Parallel(n_jobs=-1)(
        joblib.delayed(executar_algoritmo)(execucao, grupo, dados, 
                                           num_avaliacoes, instancia)
        for execucao in range(num_execucoes)
    )
    