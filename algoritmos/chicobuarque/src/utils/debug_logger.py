# src/utils/debug_logger.py
"""
Módulo de Logging para Debug de Violações de Janelas de Tempo
--------------------------------------------------------------
Fornece logging detalhado em arquivos .txt para rastrear problemas
de validação de janelas de tempo.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import os


class DebugLogger:
    """
    Logger que escreve detalhes de debug em arquivos .txt.

    Cada logger cria um conjunto de arquivos timestamped na pasta logs/
    """

    def __init__(self, base_dir: str = "logs"):
        """
        Inicializa logger com timestamp único.

        Args:
            base_dir: Diretório base para arquivos de log
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp único para esta execução
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Arquivos de log
        self.files = {
            "main": self.base_dir / f"debug_media_{self.timestamp}.txt",
            "conversion": self.base_dir / f"conversao_media_{self.timestamp}.txt",
            "pre_validation": self.base_dir / f"pre_validacao_media_{self.timestamp}.txt",
            "vns_integrity": self.base_dir / f"vns_integrity_{self.timestamp}.txt",
            "report": self.base_dir / f"relatorio_final_{self.timestamp}.txt",
        }

        # Inicializar arquivos
        for file_path in self.files.values():
            file_path.write_text(f"=== Log iniciado em {datetime.now()} ===\n\n")

    def log(self, category: str, message: str):
        """
        Escreve mensagem em arquivo de log específico.

        Args:
            category: Categoria do log (main, conversion, pre_validation, etc.)
            message: Mensagem a ser logada
        """
        if category not in self.files:
            category = "main"

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with open(self.files[category], "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    def log_grasp_start(self, inst_n: int, budget: int):
        """Loga início do GRASP."""
        msg = f"""
{'='*70}
FASE GRASP INICIADA
{'='*70}
Instância: {inst_n} requisições
Budget: {budget} avaliações
"""
        self.log("main", msg)

    def log_vns_start(self, budget: int):
        """Loga início do VNS."""
        msg = f"""
{'='*70}
FASE VNS INICIADA
{'='*70}
Budget: {budget} avaliações
"""
        self.log("main", msg)

    def log_solution_stats(self, sol: Any, inst: Any, phase: str):
        """
        Loga estatísticas de uma solução.

        Args:
            sol: Objeto Solution
            inst: Objeto Instance
            phase: Fase da execução (GRASP, VNS, etc.)
        """
        # Calcular cobertura
        atendidas = set()
        for k in sol.routes:
            for trip in sol.routes[k]:
                atendidas.update(n for n in trip if n != 0)

        cobertura = len(atendidas) / inst.n if inst.n > 0 else 0.0
        custo = sol.total_cost()

        msg = f"""
--- Estatísticas da Solução ({phase}) ---
Custo: {custo:.2f}
Cobertura: {len(atendidas)}/{inst.n} ({cobertura*100:.1f}%)
Viagens utilizadas: {sum(len(sol.routes[k]) for k in sol.routes)}
"""
        self.log("main", msg)

    def log_conversion_start(self):
        """Loga início da conversão."""
        self.log("conversion", f"\n{'='*70}\nCONVERSÃO SOLUTION -> SOLUCAO\n{'='*70}\n")

    def log_vehicle_conversion(self, k: int, v_idx: int, trip: List[int],
                               acc_antes: float, arr: List[float],
                               acc_depois: float, inst: Any):
        """
        Loga detalhes da conversão de uma viagem.

        Args:
            k: Índice do veículo (0-based)
            v_idx: Índice da viagem (1-based)
            trip: Rota da viagem
            acc_antes: Tempo acumulado antes da viagem
            arr: Tempos de chegada calculados
            acc_depois: Tempo acumulado após a viagem
            inst: Instância
        """
        espera = arr[0] - acc_antes if len(arr) > 0 else 0.0
        alerta = " ⚠️  ESPERA LONGA!" if espera > 50.0 else ""

        msg = f"""
Veículo {k+1}, Viagem {v_idx}:
  Rota: {trip}
  acc_antes:  {acc_antes:8.2f}
  arr[0]:     {arr[0]:8.2f}  (espera: {espera:6.2f}){alerta}
  arr[-1]:    {arr[-1]:8.2f}
  s[0]:       {inst.s[0]:8.2f}
  acc_depois: {acc_depois:8.2f}
"""

        # Se houver janelas de tempo, logar validação
        if inst.e is not None and inst.l is not None:
            msg += "  Validação de janelas:\n"
            for idx, node in enumerate(trip):
                if node == 0:
                    continue
                e_i = inst.e[node - 1]
                l_i = inst.l[node - 1]
                a_i = arr[idx]
                status = "✅" if e_i - 1e-9 <= a_i <= l_i + 1e-9 else "❌ VIOLA"
                msg += f"    node {node:3d}: arr={a_i:7.2f}, win=[{e_i:6.2f}, {l_i:6.2f}] {status}\n"

        self.log("conversion", msg)

    def log_pre_validation(self, violations: List[Dict[str, Any]]):
        """
        Loga resultados da pré-validação.

        Args:
            violations: Lista de violações detectadas
        """
        if not violations:
            self.log("pre_validation", "✅ Nenhuma violação detectada na pré-validação!\n")
        else:
            msg = f"❌ {len(violations)} violações detectadas:\n\n"
            for v in violations:
                msg += f"  Requisição {v['node']}: "
                msg += f"chegada={v['arrival']:.2f}, "
                msg += f"janela=[{v['e']:.2f}, {v['l']:.2f}]\n"
            self.log("pre_validation", msg)

    def log_vns_integrity_call(self, call_count: int):
        """Loga chamada de ensure_route_integrity."""
        self.log("vns_integrity", f"Chamada #{call_count} de ensure_route_integrity()")

    def log_final_report(self, grasp_cost: float, vns_cost: float,
                        final_cost: float, pre_violations: int, post_violations: int):
        """
        Loga relatório final comparativo.

        Args:
            grasp_cost: Custo da solução GRASP
            vns_cost: Custo da solução VNS
            final_cost: Custo da solução final convertida
            pre_violations: Violações antes da conversão
            post_violations: Violações após validação externa
        """
        msg = f"""
{'='*70}
RELATÓRIO FINAL DE DEBUG
{'='*70}

CUSTOS:
  GRASP:     {grasp_cost:12.2f}
  VNS:       {vns_cost:12.2f}
  Final:     {final_cost:12.2f}

VIOLAÇÕES:
  Pré-conversão:      {pre_violations:4d}
  Pós-validação:      {post_violations:4d}

DIAGNÓSTICO:
"""

        if pre_violations == 0 and post_violations > 0:
            msg += "  ❌ BUG NA CONVERSÃO! Solução interna OK, mas conversão introduz violações.\n"
        elif pre_violations > 0 and post_violations > 0:
            msg += "  ❌ BUG NO VNS! Solução já tem violações antes da conversão.\n"
        elif pre_violations == 0 and post_violations == 0:
            msg += "  ✅ TUDO OK! Solução válida em todas as etapas.\n"

        msg += f"\n{'='*70}\n"
        msg += f"Logs salvos em: {self.base_dir}/\n"
        msg += f"  - debug_media_{self.timestamp}.txt\n"
        msg += f"  - conversao_media_{self.timestamp}.txt\n"
        msg += f"  - pre_validacao_media_{self.timestamp}.txt\n"
        msg += f"  - vns_integrity_{self.timestamp}.txt\n"
        msg += f"  - relatorio_final_{self.timestamp}.txt\n"
        msg += f"{'='*70}\n"

        self.log("report", msg)
        print(msg)  # Também imprime no console

    def get_log_dir(self) -> str:
        """Retorna caminho do diretório de logs."""
        return str(self.base_dir)
