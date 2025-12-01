#!/usr/bin/env python3
"""
Script de Simulação - Formato de Entrega do André
--------------------------------------------------
Simula EXATAMENTE o que o professor vai executar para testar sua solução.

Este script:
1. Carrega uma instância
2. Chama resolva() como o professor fará
3. Valida o formato da saída
4. Mostra a estrutura EXATA que o André vai receber
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from andre_repositorio.dados import carrega_dados_json
from chicobuarque import resolva


def mostrar_solucao_formato_andre(solucao, dados, nome_instancia):
    """
    Mostra a solução EXATAMENTE como o André vai receber.
    """
    print("\n" + "=" * 80)
    print(f"FORMATO DE SAÍDA - INSTÂNCIA: {nome_instancia.upper()}")
    print("=" * 80)
    
    print("\n📋 ESTRUTURA DA SOLUÇÃO (tipo Solucao):")
    print("-" * 80)
    
    # 1. Mostrar tipo
    print(f"Tipo do retorno: {type(solucao).__name__}")
    
    # 2. Mostrar atributo fx
    print(f"\n💰 solucao.fx (função objetivo):")
    print(f"   Tipo: {type(solucao.fx).__name__}")
    print(f"   Valor: {solucao.fx:.2f}")
    
    # 3. Mostrar estrutura de rota
    print(f"\n🚌 solucao.rota (dicionário de rotas):")
    print(f"   Tipo: {type(solucao.rota).__name__}")
    print(f"   Keys (ônibus): {list(solucao.rota.keys())}")
    
    # Mostrar algumas rotas de exemplo
    print(f"\n   Exemplos de rotas:")
    viagens_mostradas = 0
    for k in range(1, min(dados.K + 1, 4)):  # mostrar até 3 ônibus
        if k not in solucao.rota:
            continue
        
        viagens_nao_vazias = []
        for v in range(1, dados.r + 1):
            if solucao.rota[k][v]:  # se não está vazia
                viagens_nao_vazias.append(v)
        
        if viagens_nao_vazias:
            print(f"\n   Ônibus {k}:")
            for v in viagens_nao_vazias[:2]:  # mostrar até 2 viagens por ônibus
                rota = solucao.rota[k][v]
                print(f"      rota[{k}][{v}] = {rota}")
                viagens_mostradas += 1
                
                if viagens_mostradas >= 5:  # limitar total de exemplos
                    break
        
        if viagens_mostradas >= 5:
            break
    
    # 4. Mostrar estrutura de chegada
    print(f"\n⏰ solucao.chegada (dicionário de tempos):")
    print(f"   Tipo: {type(solucao.chegada).__name__}")
    print(f"   Keys (ônibus): {list(solucao.chegada.keys())}")
    
    # Mostrar alguns tempos de exemplo
    print(f"\n   Exemplos de tempos de chegada:")
    tempos_mostrados = 0
    for k in range(1, min(dados.K + 1, 4)):
        if k not in solucao.chegada:
            continue
        
        viagens_nao_vazias = []
        for v in range(1, dados.r + 1):
            if solucao.chegada[k][v]:
                viagens_nao_vazias.append(v)
        
        if viagens_nao_vazias:
            print(f"\n   Ônibus {k}:")
            for v in viagens_nao_vazias[:2]:
                chegada = solucao.chegada[k][v]
                # Formatar tempos com 2 casas decimais
                chegada_formatada = [f"{t:.2f}" for t in chegada]
                print(f"      chegada[{k}][{v}] = {chegada_formatada}")
                tempos_mostrados += 1
                
                if tempos_mostrados >= 5:
                    break
        
        if tempos_mostrados >= 5:
            break
    
    # 5. Validações automáticas
    print("\n" + "=" * 80)
    print("VALIDAÇÕES AUTOMÁTICAS (o que o André vai verificar)")
    print("=" * 80)
    
    validacoes = []
    
    # Validação 1: Atributos existem
    tem_rota = hasattr(solucao, 'rota')
    tem_chegada = hasattr(solucao, 'chegada')
    tem_fx = hasattr(solucao, 'fx')
    
    validacoes.append(("Atributo 'rota' existe", tem_rota))
    validacoes.append(("Atributo 'chegada' existe", tem_chegada))
    validacoes.append(("Atributo 'fx' existe", tem_fx))
    
    # Validação 2: Tipos corretos
    validacoes.append(("rota é dicionário", isinstance(solucao.rota, dict)))
    validacoes.append(("chegada é dicionário", isinstance(solucao.chegada, dict)))
    validacoes.append(("fx é numérico", isinstance(solucao.fx, (int, float))))
    
    # Validação 3: Todos os ônibus e viagens presentes
    todos_onibus = all(k in solucao.rota for k in range(1, dados.K + 1))
    validacoes.append((f"Todos {dados.K} ônibus em 'rota'", todos_onibus))
    
    todas_viagens_ok = True
    for k in range(1, dados.K + 1):
        if k not in solucao.rota or not isinstance(solucao.rota[k], dict):
            todas_viagens_ok = False
            break
        for v in range(1, dados.r + 1):
            if v not in solucao.rota[k]:
                todas_viagens_ok = False
                break
    
    validacoes.append((f"Todas {dados.r} viagens por ônibus", todas_viagens_ok))
    
    # Validação 4: Rotas começam e terminam em 0
    rotas_validas = True
    rotas_problematicas = []
    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            rota = solucao.rota[k][v]
            if rota and len(rota) > 0:
                if rota[0] != 0 or rota[-1] != 0:
                    rotas_validas = False
                    rotas_problematicas.append((k, v, rota))
    
    validacoes.append(("Rotas começam/terminam em 0", rotas_validas))
    
    # Validação 5: Correspondência rota-chegada
    correspondencia_ok = True
    erros_correspondencia = []
    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            len_rota = len(solucao.rota[k][v])
            len_chegada = len(solucao.chegada[k][v])
            if len_rota != len_chegada:
                correspondencia_ok = False
                erros_correspondencia.append((k, v, len_rota, len_chegada))
    
    validacoes.append(("Correspondência rota-chegada", correspondencia_ok))
    
    # Validação 6: Cobertura de requisições
    requisicoes_atendidas = set()
    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            requisicoes_atendidas.update(n for n in solucao.rota[k][v] if n != 0)
    
    cobertura = len(requisicoes_atendidas) / dados.n
    validacoes.append((f"Cobertura: {len(requisicoes_atendidas)}/{dados.n} ({cobertura*100:.1f}%)", 
                       cobertura == 1.0))
    
    # Mostrar resultados
    print()
    for descricao, passou in validacoes:
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"  {status} - {descricao}")
    
    # Mostrar erros específicos se houver
    if rotas_problematicas:
        print("\n  ⚠️  ROTAS PROBLEMÁTICAS:")
        for k, v, rota in rotas_problematicas[:3]:
            print(f"      Ônibus {k}, Viagem {v}: {rota}")
    
    if erros_correspondencia:
        print("\n  ⚠️  ERROS DE CORRESPONDÊNCIA:")
        for k, v, lr, lc in erros_correspondencia[:3]:
            print(f"      Ônibus {k}, Viagem {v}: len(rota)={lr}, len(chegada)={lc}")
    
    # Resumo final
    total_validacoes = len(validacoes)
    validacoes_ok = sum(1 for _, passou in validacoes if passou)
    
    print("\n" + "=" * 80)
    if validacoes_ok == total_validacoes:
        print(f"✅ RESULTADO: {validacoes_ok}/{total_validacoes} validações PASSARAM")
        print("🎉 Solução está no formato CORRETO para o André!")
    else:
        print(f"❌ RESULTADO: {validacoes_ok}/{total_validacoes} validações passaram")
        print("⚠️  Corrija os erros acima antes de entregar!")
    print("=" * 80)
    
    return validacoes_ok == total_validacoes


def simular_execucao_andre(nome_instancia):
    """
    Simula EXATAMENTE o que o André vai executar.
    """
    print("\n" + "=" * 80)
    print("SIMULAÇÃO DA EXECUÇÃO DO PROFESSOR")
    print("=" * 80)
    print(f"\nInstância: {nome_instancia}")
    
    # 1. Carregar dados (como o André fará)
    print("\n[1] Carregando instância...")
    filepath = f"andre_repositorio/dados/{nome_instancia}.json"
    dados = carrega_dados_json(filepath)
    
    print(f"    ✓ Instância carregada")
    print(f"      - n (requisições): {dados.n}")
    print(f"      - K (ônibus): {dados.K}")
    print(f"      - r (viagens/ônibus): {dados.r}")
    print(f"      - Tmax: {dados.Tmax}")
    
    # 2. Calcular número de avaliações (como o André fará)
    print("\n[2] Calculando número de avaliações...")
    numero_avaliacoes = 10 * dados.n * dados.K * dados.r
    print(f"    ✓ N_max_av = 10 × {dados.n} × {dados.K} × {dados.r} = {numero_avaliacoes}")
    
    # 3. Executar algoritmo (EXATAMENTE como o André fará)
    print("\n[3] Executando: solucao = resolva(dados, numero_avaliacoes)")
    print("    Aguarde...")
    
    try:
        solucao = resolva(dados, numero_avaliacoes)
        print(f"    ✓ Execução concluída com sucesso!")
    except Exception as e:
        print(f"    ❌ ERRO durante execução:")
        print(f"       {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Mostrar o que o André vai receber
    print("\n[4] Analisando saída recebida...")
    sucesso = mostrar_solucao_formato_andre(solucao, dados, nome_instancia)
    
    return sucesso


def main():
    """
    Executa simulação em instâncias selecionadas.
    """
    print("=" * 80)
    print("SIMULADOR DE EXECUÇÃO - FORMATO DO ANDRÉ")
    print("=" * 80)
    print("\nEste script simula EXATAMENTE o que o professor vai executar:")
    print("1. Carrega instância JSON")
    print("2. Calcula N_max_av = 10 × n × K × r")
    print("3. Chama: solucao = resolva(dados, numero_avaliacoes)")
    print("4. Valida formato da solução retornada")
    print("5. Mostra estrutura EXATA recebida")
    
    # Escolher instâncias para testar
    instancias = ['pequena']  # começar com a pequena
    
    resultados = {}
    
    for instancia in instancias:
        try:
            sucesso = simular_execucao_andre(instancia)
            resultados[instancia] = "✅ OK" if sucesso else "❌ FALHOU"
        except Exception as e:
            print(f"\n❌ ERRO FATAL na instância {instancia}:")
            print(f"   {e}")
            import traceback
            traceback.print_exc()
            resultados[instancia] = "❌ ERRO"
    
    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO GERAL")
    print("=" * 80)
    
    for instancia, resultado in resultados.items():
        print(f"  {instancia:15s}: {resultado}")
    
    print("\n" + "=" * 80)
    if all("✅" in r for r in resultados.values()):
        print("🎉 SUCESSO! Todas as instâncias estão no formato correto!")
        print("Seu código está pronto para o professor testar.")
        return 0
    else:
        print("⚠️  Algumas instâncias falharam. Revise os erros acima.")
        return 1


if __name__ == "__main__":
    sys.exit(main())