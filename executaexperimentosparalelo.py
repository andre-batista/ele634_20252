import sys
import os
from dados import carrega_dados_json
import joblib
import random
import numpy as np

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
instancia = ['grande', 'rush']  # Opções: 'pequena', 'media', 'grande', 'rush'
num_avaliacoes = [118800, 118800] # 2100, 48240, 118800, 118800
num_execucoes = 30
grupos = ["alcione"]



def executar_algoritmo(execucao, grupo, dados, num_avaliacoes, instancia):
    # Configurar semente única para cada execução
    seed = execucao  # Cada execução usa sua própria semente (0, 1, 2, ..., 29)
    random.seed(seed)
    np.random.seed(seed)
    
    if grupo == "alcione":
        solucao = resolva_alcione(dados, numero_avaliacoes=num_avaliacoes)
    elif grupo == "cartola":
        solucao = resolva_cartola(dados, numero_avaliacoes=num_avaliacoes)
    elif grupo == "chicobuarque":
        solucao = resolva_chicobuarque(dados, numero_avaliacoes=num_avaliacoes)
    elif grupo == "djavan":
        solucao = resolva_djavan(dados, numero_avaliacoes=num_avaliacoes)
    elif grupo == "seujorge":
        solucao = resolva_seujorge(dados, numero_avaliacoes=num_avaliacoes)

    # Salvar imediatamente após gerar a solução
    solucao.salvar("./resultados/{}/{}/s{}.json".format(instancia, grupo, execucao + 1))
    
    return solucao

for instancia, num_avaliacoes in zip(instancia, num_avaliacoes):

    dados = carrega_dados_json(f'./dados/{instancia}.json')

    print(f'Instância {instancia} carregada com sucesso.')

    for grupo in grupos:

        print(f'Executando grupo: {grupo}')

        os.makedirs(f'./resultados/{instancia}/{grupo}', exist_ok=True)

        # Executar em paralelo (cada execução salva sua própria solução)
        joblib.Parallel(n_jobs=-1, verbose=10)(
            joblib.delayed(executar_algoritmo)(execucao, grupo, dados, 
                                               num_avaliacoes, instancia)
            for execucao in range(num_execucoes)
        )
        
        print(f'✅ Grupo {grupo} concluído!\n')
        
    
    