"""
Script de debug para analisar soluções e identificar inconsistências de tempo.
Mostra exatamente onde a validação do método factivel() falha.
"""

import json
from andre_repositorio.dados import carrega_dados_json
from andre_repositorio.solucao import Solucao


def debug_solucao(instancia_nome, solucao_arquivo):
    """
    Debug detalhado de uma solução para identificar problemas de factibilidade.

    Args:
        instancia_nome: Nome da instância (ex: 'pequena')
        solucao_arquivo: Caminho do arquivo JSON da solução
    """
    print("\n" + "=" * 100)
    print(f"DEBUG: {instancia_nome.upper()} - {solucao_arquivo}")
    print("=" * 100)

    # Carregar dados
    instancia_path = f"andre_repositorio/dados/{instancia_nome}.json"
    dados = carrega_dados_json(instancia_path)

    print(f"\nDados da instância:")
    print(f"  n={dados.n}, K={dados.K}, r={dados.r}, Tmax={dados.Tmax}")
    print(f"  s[0] (tempo serviço garagem) = {dados.s[0]}")

    # Carregar solução
    solucao = Solucao()
    try:
        solucao.carregar(solucao_arquivo)
    except FileNotFoundError:
        print(f"\n❌ Arquivo não encontrado: {solucao_arquivo}")
        return

    print(f"  fx (custo total) = {solucao.fx}")

    # Analisar cada veículo e viagem
    problemas = []
    N = list(range(1, dados.n + 1))  # Lista de requisições

    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            if v not in solucao.rota[k] or not solucao.rota[k][v]:
                continue

            rota = solucao.rota[k][v]
            chegada = solucao.chegada[k][v]

            print(f"\n{'─' * 100}")
            print(f"Veículo {k}, Viagem {v}:")
            print(f"  Rota: {rota}")
            print(f"  Chegadas: {[f'{t:.2f}' for t in chegada]}")

            # Verificar consistência temporal entre nós consecutivos
            for i in range(1, len(rota)):
                no_anterior = rota[i-1]
                no_atual = rota[i]
                chegada_anterior = chegada[i-1]
                chegada_atual = chegada[i]

                # Calcular tempo esperado
                tempo_servico = dados.s[no_anterior]
                tempo_viagem = dados.T[no_anterior, no_atual]
                tempo_minimo_necessario = chegada_anterior + tempo_servico + tempo_viagem

                # Verificar se há inconsistência
                tolerancia = 1e-4
                diferenca = tempo_minimo_necessario - chegada_atual

                if diferenca > tolerancia:
                    msg = (f"  ❌ INCONSISTÊNCIA [{no_anterior}→{no_atual}]: "
                           f"chegada_ant={chegada_anterior:.4f} + "
                           f"s[{no_anterior}]={tempo_servico:.4f} + "
                           f"T[{no_anterior}→{no_atual}]={tempo_viagem:.4f} = "
                           f"{tempo_minimo_necessario:.4f} > "
                           f"chegada_atual={chegada_atual:.4f} "
                           f"(diferença: {diferenca:.6f})")
                    print(msg)
                    problemas.append({
                        'veiculo': k,
                        'viagem': v,
                        'de': no_anterior,
                        'para': no_atual,
                        'diferenca': diferenca,
                        'detalhes': msg
                    })
                else:
                    folga = chegada_atual - tempo_minimo_necessario
                    print(f"  ✓ OK [{no_anterior}→{no_atual}]: "
                          f"tempo_necessario={tempo_minimo_necessario:.4f}, "
                          f"chegada={chegada_atual:.4f}, "
                          f"folga={folga:.6f}")

            # Verificar duração da viagem
            duracao = chegada[-1] - chegada[0]
            if duracao > dados.Tmax + 1e-4:
                msg = f"  ❌ DURAÇÃO EXCEDIDA: {duracao:.4f} > Tmax={dados.Tmax}"
                print(msg)
                problemas.append({
                    'veiculo': k,
                    'viagem': v,
                    'tipo': 'duracao',
                    'detalhes': msg
                })
            else:
                print(f"  ✓ Duração OK: {duracao:.4f} <= Tmax={dados.Tmax}")

            # Verificar janelas de tempo
            for i in range(1, len(rota) - 1):  # Excluir garagem (0)
                requisicao = rota[i]
                t_chegada = chegada[i]
                e_i = dados.e[requisicao - 1]
                l_i = dados.l[requisicao - 1]

                if t_chegada < e_i - 2e-4 or t_chegada > l_i + 2e-4:
                    msg = (f"  ❌ JANELA VIOLADA req={requisicao}: "
                           f"chegada={t_chegada:.4f}, janela=[{e_i:.4f}, {l_i:.4f}]")
                    print(msg)
                    problemas.append({
                        'veiculo': k,
                        'viagem': v,
                        'requisicao': requisicao,
                        'tipo': 'janela',
                        'detalhes': msg
                    })
                else:
                    print(f"  ✓ Janela OK req={requisicao}: "
                          f"chegada={t_chegada:.4f} ∈ [{e_i:.4f}, {l_i:.4f}]")

            # Remover requisições atendidas da lista N
            for req in rota[1:-1]:  # Excluir garagem
                if req in N:
                    N.remove(req)

    # Verificar cobertura completa
    print(f"\n{'─' * 100}")
    if N:
        msg = f"❌ REQUISIÇÕES NÃO ATENDIDAS: {N}"
        print(msg)
        problemas.append({
            'tipo': 'cobertura',
            'detalhes': msg
        })
    else:
        print("✓ Todas as requisições foram atendidas")

    # Resumo de problemas
    print(f"\n{'═' * 100}")
    print("RESUMO:")
    print(f"{'═' * 100}")

    if problemas:
        print(f"\n❌ Encontrados {len(problemas)} problema(s):\n")
        for i, p in enumerate(problemas, 1):
            print(f"{i}. {p['detalhes']}")
        print(f"\n{'═' * 100}")
        return False
    else:
        print("\n✓ Nenhum problema encontrado - Solução é FACTÍVEL!")
        print(f"{'═' * 100}")
        return True


def main():
    """
    Executa debug em todas as soluções geradas.
    """
    print("\n")
    print("╔" + "═" * 98 + "╗")
    print("║" + " " * 30 + "DEBUG DE SOLUÇÕES GERADAS" + " " * 43 + "║")
    print("╚" + "═" * 98 + "╝")

    testes = [
        ("pequena", "minha_solucao_pequena.json"),
        ("media", "minha_solucao_media.json"),
        ("grande", "minha_solucao_grande.json"),
    ]

    resultados = {}

    for instancia, arquivo in testes:
        try:
            resultado = debug_solucao(instancia, arquivo)
            resultados[instancia] = resultado
        except Exception as e:
            print(f"\n❌ ERRO ao debugar {instancia}: {e}")
            import traceback
            traceback.print_exc()
            resultados[instancia] = False

    # Resumo final
    print("\n")
    print("╔" + "═" * 98 + "╗")
    print("║" + " " * 40 + "RESUMO FINAL" + " " * 46 + "║")
    print("╚" + "═" * 98 + "╝")
    print()

    for instancia, resultado in resultados.items():
        status = "✓ FACTÍVEL" if resultado else "✗ INFACTÍVEL"
        print(f"  {instancia:15s} : {status}")

    print()


if __name__ == "__main__":
    main()
