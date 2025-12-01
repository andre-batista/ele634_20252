# tests/test_validacao_semana1.py
from pathlib import Path
import sys
"""
Teste (Semana 1): validação básica dos dados carregados.
Confere n, K, r, Tmax e tipos/formatos de D/T/c/s.
"""

# garantir acesso ao andre_repositorio
HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
ANDRE = ROOT / "andre_repositorio"
if str(ANDRE) not in sys.path:
    sys.path.insert(0, str(ANDRE))

def _shape_ok(M, n_plus_1):
    try:
        return len(M) == n_plus_1 and all(len(row) == n_plus_1 for row in M)
    except Exception:
        return False

def _nonneg(M):
    for row in M:
        for v in (row if hasattr(row, "__iter__") else [row]):
            if v < 0:
                return False
    return True

def _diag_zero(M):
    for i in range(len(M)):
        if M[i][i] != 0:
            return False
    return True

def validar_instancia(json_path: Path):
    from dados import carrega_dados_json
    dados = carrega_dados_json(str(json_path))

    # campos essenciais
    n   = getattr(dados, "n")
    K   = getattr(dados, "K")
    r   = getattr(dados, "r")
    Tmax= getattr(dados, "Tmax", getattr(dados, "tempoMaximo", None))
    D   = getattr(dados, "D")
    T   = getattr(dados, "T")
    c   = getattr(dados, "c")
    s   = getattr(dados, "s")
    e   = getattr(dados, "inicioJanela", None)
    l   = getattr(dados, "fimJanela", None)

    # 1) tipos/valores básicos
    assert isinstance(n, int) and n >= 1, "n inválido"
    assert isinstance(K, int) and K >= 1, "K inválido"
    assert isinstance(r, int) and r >= 1, "r inválido"
    assert Tmax is not None and Tmax > 0, "Tmax ausente ou inválido"

    n1 = n + 1  # inclui depósito

    # 2) dimensões e não-negatividade
    for name, M in [("D", D), ("T", T), ("c", c)]:
        assert _shape_ok(M, n1), f"{name} deve ser {n1}x{n1}"
        assert _nonneg(M), f"{name} possui valores negativos"
        assert _diag_zero(M), f"{name} deve ter diagonal = 0"

    # 3) serviço e janelas (se existirem)
    assert len(s) == n1, "s deve ter n+1 elementos"
    assert _nonneg(s), "s possui valores negativos"

    if e is not None and l is not None:
        assert len(e) == n1 and len(l) == n1, "e/l devem ter n+1"
        for ei, li in zip(e, l):
            assert ei <= li, "encontrado e > l"

    # 4) depósito conectável (ex.: distâncias saída/retorno)
    for j in range(1, n1):
        assert D[0][j] >= 0 and D[j][0] >= 0, "D inválido para depósito"

    print(f"[OK] {json_path.name}: validação básica passou ✓")
    print(f"Resumo: n={n}, K={K}, r={r}, Tmax={Tmax}")

def main():
    base = ROOT / "andre_repositorio" / "dados"
    for nome in ("pequena.json", "media.json"):
        p = base / nome
        if p.exists():
            validar_instancia(p)
        else:
            print(f"[WARN] arquivo não encontrado: {p}")

if __name__ == "__main__":
    main()
