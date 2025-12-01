from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

"""
Adapter: Loader do André -> Instance interna
--------------------------------------------
Funções para carregar as instâncias no formato do André (JSON/Dados)
e convertê-las para o objeto `Instance` usado internamente.

Usos:
- Scripts de checagem/resumo (Semana 1).
- Testes que precisam de `Instance` (Semanas 1–2).
"""

def load_andre_instance(path_json: str) -> Dict[str, Any]:
    """
    Lê uma instância via andre_repositorio.dados e normaliza nomes de campos.
    Retorna um dicionário padronizado para o resto do projeto.
    """
    from importlib import import_module
    dados_mod = import_module("dados")  # dentro de andre_repositorio
    carrega = getattr(dados_mod, "carrega_dados_json")
    d = carrega(str(Path(path_json)))

    # normalização
    Tmax = getattr(d, "Tmax", getattr(d, "tempoMaximo", None))
    e = getattr(d, "e", getattr(d, "inicioJanela", None))
    l = getattr(d, "l", getattr(d, "fimJanela", None))

    return {
        "n": d.n, "K": d.K, "r": d.r, "Tmax": Tmax,
        "D": d.D, "T": d.T, "c": d.c, "s": d.s,
        "e": e, "l": l,
    }
