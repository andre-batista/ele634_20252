import json
from pathlib import Path
from dados_base import DadosBase

path = Path(__file__).parents[1] / "scripts" / "instancia_toy.json"
with open(path, "r") as f:
    raw = json.load(f)

dados = DadosBase(
    n=raw["n"], K=raw["K"], r=raw["r"], Tmax=raw["Tmax"],
    d={tuple(map(int,k.split(","))):v for k,v in raw["d"].items()},
    t={tuple(map(int,k.split(","))):v for k,v in raw["t"].items()},
    c={tuple(map(int,k.split(","))):v for k,v in raw["c"].items()},
    s={int(k):v for k,v in raw["s"].items()},
    e={int(k):v for k,v in raw["e"].items()},
    l={int(k):v for k,v in raw["l"].items()},
)

print("[OK] Instância toy carregada:", dados)
