"""
Comparacao os valores obtidos pela nossa solucao com os valores otimos do André.
"""

import time
import json
from andre_repositorio.dados import carrega_dados_json
from chicobuarque import resolva


def carregar_otimo(instancia_nome):
    """Carrega solucao otima do JSON."""
    otimo_path = f"andre_repositorio/dados/otimo_{instancia_nome}.json"
    try:
        with open(otimo_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def analisar_solucao_otima(solucao_otima):
    """Extrai metricas da solucao otima."""
    if not solucao_otima or 'onibus' not in solucao_otima:
        return None

    fx = solucao_otima.get('fx', 0)
    total_viagens = 0
    total_onibus = 0
    requisicoes_atendidas = set()

    for onibus_id, viagens in solucao_otima['onibus'].items():
        if viagens:
            total_onibus += 1
            for viagem_id, viagem_data in viagens.items():
                total_viagens += 1
                rota = viagem_data.get('rota', [])
                requisicoes_atendidas.update([r for r in rota if r != 0])

    return {
        'fx': fx,
        'viagens': total_viagens,
        'onibus': total_onibus,
        'requisicoes': len(requisicoes_atendidas)
    }


def analisar_sua_solucao(solucao, dados):
    """Extrai metricas da sua solucao."""
    fx = solucao.fx
    total_viagens = 0
    total_onibus = 0
    requisicoes_atendidas = set()

    for k in range(1, dados.K + 1):
        onibus_usado = False
        if k in solucao.rota:
            for v in solucao.rota[k].keys():
                rota = solucao.rota[k][v]
                if rota and len(rota) > 0:
                    total_viagens += 1
                    onibus_usado = True
                    requisicoes_atendidas.update([r for r in rota if r != 0])
        if onibus_usado:
            total_onibus += 1

    return {
        'fx': fx,
        'viagens': total_viagens,
        'onibus': total_onibus,
        'requisicoes': len(requisicoes_atendidas)
    }


def testar_instancia(instancia_nome):
    """Testa uma instancia e retorna metricas."""
    print(f"\n{'='*80}")
    print(f"INSTANCIA: {instancia_nome.upper()}")
    print('='*80)

    # Carregar dados
    instancia_path = f"andre_repositorio/dados/{instancia_nome}.json"
    try:
        dados = carrega_dados_json(instancia_path)
    except Exception as e:
        print(f"ERRO ao carregar: {e}")
        return None

    numero_avaliacoes = 10 * dados.n * dados.K * dados.r

    print(f"\nParametros:")
    print(f"  Requisicoes:  {dados.n}")
    print(f"  Onibus:       {dados.K}")
    print(f"  Viagens/onibus: {dados.r}")
    print(f"  Tmax:         {dados.Tmax:.1f}")
    print(f"  Budget:       {numero_avaliacoes:,}")

    # Carregar otimo
    solucao_otima_json = carregar_otimo(instancia_nome)
    if solucao_otima_json:
        metricas_otimo = analisar_solucao_otima(solucao_otima_json)
        fx_otimo = metricas_otimo['fx']
        viagens_otimo = metricas_otimo['viagens']
        print(f"\nSolucao Otima:")
        print(f"  Custo:    {fx_otimo:,.2f}")
        print(f"  Viagens:  {viagens_otimo}")
    else:
        metricas_otimo = None
        fx_otimo = None
        viagens_otimo = None
        print(f"\nSolucao Otima: NAO DISPONIVEL")

    # Executar algoritmo
    print(f"\nExecutando algoritmo...")
    tempo_inicio = time.time()
    try:
        solucao = resolva(dados, numero_avaliacoes)
        tempo_execucao = time.time() - tempo_inicio
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None

    metricas_sua = analisar_sua_solucao(solucao, dados)
    fx_seu = metricas_sua['fx']
    viagens_suas = metricas_sua['viagens']

    print(f"\nSua Solucao:")
    print(f"  Custo:    {fx_seu:,.2f}")
    print(f"  Viagens:  {viagens_suas}")
    print(f"  Onibus:   {metricas_sua['onibus']}/{dados.K}")
    print(f"  Cobertura: {metricas_sua['requisicoes']}/{dados.n}")
    print(f"  Tempo:    {tempo_execucao:.2f}s")

    # Calcular GAP
    if fx_otimo and fx_otimo > 0:
        gap = ((fx_seu - fx_otimo) / fx_otimo) * 100
        diferenca = fx_seu - fx_otimo

        print(f"\n{'-'*80}")
        print(f"COMPARACAO:")
        print(f"  Otimo:      {fx_otimo:>15,.2f}")
        print(f"  Seu:        {fx_seu:>15,.2f}")
        print(f"  Diferenca:  {diferenca:>+15,.2f}")
        print(f"  GAP:        {gap:>+15.2f}%")
        print(f"{'-'*80}")

        # Classificacao
        if gap <= 0:
            nota = "A+"
            status = "EXCELENTE - Melhor ou igual ao otimo!"
        elif gap <= 1:
            nota = "A"
            status = "EXCEPCIONAL - GAP < 1%"
        elif gap <= 3:
            nota = "B+"
            status = "MUITO BOM - GAP < 3%"
        elif gap <= 5:
            nota = "B"
            status = "BOM - GAP < 5%"
        elif gap <= 10:
            nota = "C"
            status = "RAZOAVEL - GAP < 10%"
        else:
            nota = "D"
            status = "PRECISA MELHORAR - GAP > 10%"

        print(f"\nAvaliacao: {nota} - {status}")
    else:
        gap = None
        nota = "N/A"
        status = "Sem comparacao"

    return {
        'instancia': instancia_nome,
        'n': dados.n,
        'K': dados.K,
        'r': dados.r,
        'fx_otimo': fx_otimo,
        'fx_seu': fx_seu,
        'gap': gap,
        'nota': nota,
        'viagens_otimo': viagens_otimo,
        'viagens_suas': viagens_suas,
        'tempo': tempo_execucao,
    }


def main():
    """Executa teste em todas as instancias."""
    print("\n")
    print("="*80)
    print("COMPARACAO COMPLETA - OTIMO vs SUA SOLUCAO")
    print("Algoritmo: chicobuarque.py (GRASP + VNS)")
    print("="*80)

    instancias = ["pequena", "media", "grande", "rush"]
    resultados = []

    for inst in instancias:
        try:
            resultado = testar_instancia(inst)
            if resultado:
                resultados.append(resultado)
        except Exception as e:
            print(f"\nERRO em {inst}: {e}")
            import traceback
            traceback.print_exc()

    # Resumo
    if not resultados:
        print("\nNenhum teste concluido")
        return

    print("\n\n")
    print("="*80)
    print("RESUMO GERAL")
    print("="*80)

    # Cabecalho
    print(f"\n{'Instancia':<12} {'Otimo':>13} {'Sua Sol.':>13} {'GAP':>9} {'Nota':>6} {'Tempo':>8}")
    print("-"*80)

    gaps_validos = []
    tempo_total = 0

    for r in resultados:
        fx_otimo_str = f"{r['fx_otimo']:,.0f}" if r['fx_otimo'] else "N/A"
        fx_seu_str = f"{r['fx_seu']:,.0f}"
        gap_str = f"{r['gap']:+.2f}%" if r['gap'] is not None else "N/A"
        tempo_str = f"{r['tempo']:.1f}s"

        print(f"{r['instancia']:<12} {fx_otimo_str:>13} {fx_seu_str:>13} {gap_str:>9} {r['nota']:>6} {tempo_str:>8}")

        if r['gap'] is not None:
            gaps_validos.append(r['gap'])
        tempo_total += r['tempo']

    print("-"*80)

    # Estatisticas
    if gaps_validos:
        gap_medio = sum(gaps_validos) / len(gaps_validos)
        gap_min = min(gaps_validos)
        gap_max = max(gaps_validos)

        print(f"\nEstatisticas:")
        print(f"  Instancias testadas:  {len(resultados)}")
        print(f"  Com solucao otima:    {len(gaps_validos)}")
        print(f"  GAP medio:            {gap_medio:+.2f}%")
        print(f"  Melhor GAP:           {gap_min:+.2f}%")
        print(f"  Pior GAP:             {gap_max:+.2f}%")
        print(f"  Tempo total:          {tempo_total:.2f}s")

        # Nota geral
        print(f"\nNota Geral:")
        if gap_medio <= 0:
            print(f"  A+ - EXCEPCIONAL! Batendo ou igualando otimos!")
        elif gap_medio <= 1:
            print(f"  A - EXCELENTE! GAP medio < 1%")
        elif gap_medio <= 3:
            print(f"  B+ - MUITO BOM! GAP medio < 3%")
        elif gap_medio <= 5:
            print(f"  B - BOM! GAP medio < 5%")
        elif gap_medio <= 10:
            print(f"  C - RAZOAVEL. GAP medio < 10%")
        else:
            print(f"  D - PRECISA MELHORAR. GAP medio > 10%")

    print("\n" + "="*80)
    print("TESTE CONCLUIDO!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
