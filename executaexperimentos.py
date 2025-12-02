import sys
from dados import carrega_dados_json

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
instancia = 'pequena'  # Opções: 'pequena', 'media', 'grande', 'rush'
dados = carrega_dados_json(f'./dados/{instancia}.json')
print(dados)

solucao = resolva_seujorge(dados, numero_avaliacoes=100)
print(solucao)