#!/usr/bin/env python3
"""
Script de Teste: GRASP + VNS
-----------------------------
Testa a implementação completa em diferentes instâncias.
"""

import sys
import os

# Adicionar diretório raiz ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Mudar para o diretório do projeto
os.chdir(project_root)

from andre_repositorio.dados import carrega_dados_json
from chicobuarque import resolva_verbose
import time


def test_instance(instance_name: str, verbose: bool = True):
    """
    Testa uma instância específica.
    
    Args:
        instance_name: Nome da instância (sem extensão .json)
        verbose: Se True, usa resolva_verbose
    """
    print("\n" + "="*80)
    print(f"TESTANDO INSTÂNCIA: {instance_name.upper()}")
    print("="*80)
    
    # Carregar dados
    filepath = f"andre_repositorio/dados/{instance_name}.json"
    dados = carrega_dados_json(filepath)
    
    # Calcular número máximo de avaliações
    numero_avaliacoes = 10 * dados.n * dados.K * dados.r
    
    print(f"\nParâmetros da instância:")
    print(f"  n (requisições): {dados.n}")
    print(f"  K (ônibus): {dados.K}")
    print(f"  r (max viagens/ônibus): {dados.r}")
    print(f"  Tmax: {dados.Tmax:.1f}")
    print(f"  Número máximo de avaliações: {numero_avaliacoes}")
    
    # Executar algoritmo
    start_time = time.time()
    
    if verbose:
        solucao, stats = resolva_verbose(dados, numero_avaliacoes)
        
        print(f"\n{'='*80}")
        print("ESTATÍSTICAS DETALHADAS")
        print(f"{'='*80}")
        for key, value in stats.items():
            print(f"  {key:25s}: {value}")
    else:
        from chicobuarque import resolva
        solucao = resolva(dados, numero_avaliacoes)
        print(f"\nCusto final: {solucao.fx:.2f}")
    
    elapsed_time = time.time() - start_time
    
    print(f"\nTempo de execução: {elapsed_time:.2f} segundos")
    
    # Validar solução
    print(f"\n{'='*80}")
    print("VALIDAÇÃO DA SOLUÇÃO")
    print(f"{'='*80}")
    
    # Verificar estrutura básica - CORRIGIDO
    total_viagens = 0
    requisicoes_atendidas = set()
    
    # Iterar corretamente sobre os ônibus e viagens
    for k in range(1, dados.K + 1):  # ônibus 1..K
        for v in range(1, dados.r + 1):  # viagens 1..r
            rota = solucao.rota[k][v]
            if rota and len(rota) > 0:  # viagem não vazia
                total_viagens += 1
                # Adicionar requisições (exceto depósito 0)
                requisicoes_atendidas.update(n for n in rota if n != 0)
    
    print(f"  Total de viagens: {total_viagens}")
    print(f"  Requisições atendidas: {len(requisicoes_atendidas)}/{dados.n}")
    print(f"  Cobertura: {len(requisicoes_atendidas)/dados.n*100:.1f}%")
    
    if len(requisicoes_atendidas) == dados.n:
        print("  ✓ Todas as requisições foram atendidas!")
    else:
        faltantes = set(range(1, dados.n + 1)) - requisicoes_atendidas
        if len(faltantes) <= 10:
            print(f"  ⚠ Requisições faltantes: {sorted(list(faltantes))}")
        else:
            print(f"  ⚠ Requisições faltantes: {sorted(list(faltantes))[:10]}... (+ {len(faltantes)-10} mais)")
    
    # Verificar formato das rotas
    rotas_ok = True
    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            rota = solucao.rota[k][v]
            if rota and len(rota) > 0:  # só verifica viagens não vazias
                if rota[0] != 0 or rota[-1] != 0:
                    print(f"  ✗ Erro: Rota k={k}, v={v} não começa/termina em 0: {rota}")
                    rotas_ok = False
    
    if rotas_ok:
        print("  ✓ Todas as rotas começam e terminam na garagem!")
    
    # Verificar correspondência rota-chegada
    correspondencia_ok = True
    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            if len(solucao.rota[k][v]) != len(solucao.chegada[k][v]):
                print(f"  ✗ Erro: Tamanhos diferentes em k={k}, v={v}")
                print(f"      rota: {len(solucao.rota[k][v])}, chegada: {len(solucao.chegada[k][v])}")
                correspondencia_ok = False
    
    if correspondencia_ok:
        print("  ✓ Correspondência rota-chegada OK!")
    
    # Verificar se há viagens com apenas depósitos [0, 0]
    viagens_vazias = 0
    for k in range(1, dados.K + 1):
        for v in range(1, dados.r + 1):
            rota = solucao.rota[k][v]
            if len(rota) == 2 and rota[0] == 0 and rota[1] == 0:
                viagens_vazias += 1
    
    if viagens_vazias > 0:
        print(f"  ℹ Info: {viagens_vazias} viagens vazias [0, 0] (normal)")
    
    print(f"\nSolução {'VÁLIDA' if (rotas_ok and correspondencia_ok) else 'INVÁLIDA'}!")
    
    return solucao, elapsed_time


def main():
    """
    Executa testes em todas as instâncias.
    """
    print("="*80)
    print("TESTES DO SISTEMA GRASP + VNS")
    print("="*80)
    
    # Lista de instâncias para testar
    instances = ['pequena', 'media']  # começar com as menores
    
    results = {}
    
    for instance in instances:
        try:
            solucao, tempo = test_instance(instance, verbose=True)
            results[instance] = {
                'custo': solucao.fx,
                'tempo': tempo,
                'status': 'OK'
            }
        except Exception as e:
            print(f"\n✗ ERRO ao processar {instance}: {e}")
            import traceback
            traceback.print_exc()
            results[instance] = {
                'custo': None,
                'tempo': None,
                'status': f'ERRO: {e}'
            }
    
    # Resumo final
    print("\n" + "="*80)
    print("RESUMO GERAL")
    print("="*80)
    
    for instance in instances:
        res = results[instance]
        if res['status'] == 'OK':
            print(f"  {instance:10s}: custo={res['custo']:12.2f}, tempo={res['tempo']:6.2f}s - {res['status']}")
        else:
            print(f"  {instance:10s}: {res['status']}")


if __name__ == "__main__":
    main()