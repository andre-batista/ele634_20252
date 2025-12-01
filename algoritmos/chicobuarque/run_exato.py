import sys
from pathlib import Path

import sys
from pathlib import Path

# pega a pasta LAB2 (pai de solucao)
ROOT = Path(__file__).resolve().parents[1]
REPO_PROF = ROOT / "ele634_20252"
sys.path.insert(0, str(REPO_PROF))

from dados import Dados, carrega_dados_json
from exato import Exato
from solucao import Solucao


def main():
    instancia = REPO_PROF / "dados" / "pequena.json"  # pode trocar por media.json
    print(f"[INFO] Usando instância: {instancia}")

    dados_dict = carrega_dados_json(str(instancia))
    dados = Dados(**dados_dict)

    modelo = Exato()
    sol: Solucao = modelo.resolve(dados)

    print("\n=== RESULTADO ===")
    print("Valor da função objetivo:", sol.valor_objetivo)
    for k, viagens in sol.rotas.items():
        for v, rota in enumerate(viagens, start=1):
            print(f"Ônibus {k}, Viagem {v}: {rota}")

    out = Path("resultados"); out.mkdir(exist_ok=True)
    sol.salvar(out / "solucao_pequena.json")
    print(f"[OK] solução salva em {out/'solucao_pequena.json'}")

if __name__ == "__main__":
    main()
