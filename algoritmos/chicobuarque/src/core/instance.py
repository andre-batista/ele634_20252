from dataclasses import dataclass
from typing import List, Optional

"""
Instance
---------
Representa a instância do problema em formato interno do projeto.

Campos principais (vindos do repositório do André):
- n, K, r, Tmax
- D, T, c : matrizes (distância, tempo de deslocamento e custo)
- s       : vetor de tempos de serviço
- e, l    : janelas de tempo (quando existirem; não usamos ainda na Semana 1–2)

Uso:
- Carregado a partir do JSON do André via `Instance.from_andre(raw_dict)`.
- É a base de dados para `Solution` e para os testes/scripts da Semana 1–2.
"""

@dataclass
class Instance:
    n: int
    K: int
    r: int
    Tmax: float
    D: List[List[float]]
    T: List[List[float]]
    c: List[List[float]]
    s: List[float]
    e: Optional[List[float]] = None
    l: Optional[List[float]] = None

    @classmethod
    def from_andre(cls, raw: dict) -> "Instance":
        return cls(**raw)
