# tests/test_resolva_interface.py
from pathlib import Path
import sys
"""
Teste (interface oficial): chama resolva(dados, numero_avaliacoes) a partir do
arquivo principal do grupo e imprime fx/rota/chegada para inspeção.
"""

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "andre_repositorio"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# importa a função resolva do arquivo na raiz
sys.path.insert(0, str(ROOT))  # para achar grupo_demo.py
from chicobuarque import resolva  # troque o nome quando renomear o arquivo

from adapters.loader_andre import load_andre_instance
from core.instance import Instance
from andre_repositorio.dados import Dados

def main():
    # carrega json e cria um 'Dados' igual o do André
    pequena = ROOT / "andre_repositorio" / "dados" / "pequena.json"
    raw = load_andre_instance(str(pequena))
    # monta o objeto Dados com os campos necessários
    dados = Dados()
    dados.n = raw["n"]; dados.K = raw["K"]; dados.r = raw["r"]; dados.Tmax = raw["Tmax"]
    dados.D = raw["D"]; dados.T = raw["T"]; dados.c = raw["c"]; dados.s = raw["s"]
    dados.e = raw.get("e"); dados.l = raw.get("l")

    sol = resolva(dados, numero_avaliacoes=10)
    # prints de sanidade
    print("fx:", sol.fx)
    print("qtd veiculos:", len(sol.rota))
    k1 = 1
    print("rota k=1 v=1:", sol.rota[k1][1])
    print("chegada k=1 v=1:", sol.chegada[k1][1])

if __name__ == "__main__":
    main()
