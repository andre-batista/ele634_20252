# tests/test_loader_semana1.py
"""
Teste (Semana 1): import do loader e carregamento de pequena/media.
Verifica se os campos básicos existem e têm dimensões esperadas.
"""

from pathlib import Path
import sys

# === garantir que o Python enxergue andre_repositorio ===
HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]  # .../lab2-solucoes
ANDRE = ROOT / "andre_repositorio"
if str(ANDRE) not in sys.path:
    sys.path.insert(0, str(ANDRE))

def _shape(x):
    try:
        r = len(x)
        c = len(x[0]) if r and hasattr(x[0], '__len__') else None
        return (r, c)
    except Exception:
        return None

def main():
    print(">>> importando carrega_dados_json de andre_repositorio/dados.py")
    try:
        from dados import carrega_dados_json
        print("[OK] import bem-sucedido")
    except Exception as e:
        print("[ERRO] falha ao importar:", repr(e))
        print("sys.path[0:3] =", sys.path[0:3])
        print("Esperado encontrar:", ANDRE)
        raise

    p = ROOT / "andre_repositorio" / "dados" / "pequena.json"
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {p}")

    print(f">>> carregando instância: {p}")
    dados = carrega_dados_json(str(p))
    print("[OK] instância carregada")

    campos = {
        "n": getattr(dados, "n", None),
        "K": getattr(dados, "K", None),
        "r": getattr(dados, "r", None),
        "Tmax": getattr(dados, "Tmax", getattr(dados, "tempoMaximo", None)),
        "D": getattr(dados, "D", None),
        "T": getattr(dados, "T", None),
        "c": getattr(dados, "c", None),
        "s": getattr(dados, "s", None),
        "e (inicioJanela)": getattr(dados, "inicioJanela", None),
        "l (fimJanela)": getattr(dados, "fimJanela", None),
    }

    print("=== RESUMO DOS CAMPOS ===")
    for k, v in campos.items():
        if isinstance(v, (list, tuple)):
            print(f"{k}: list, shape={_shape(v)}")
        else:
            print(f"{k}: {v!r}")

if __name__ == "__main__":
    main()
