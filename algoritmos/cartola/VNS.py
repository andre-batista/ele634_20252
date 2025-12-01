import time
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Optional, Tuple, Dict, Any
from Solution import Solution
from Neighborhood import Neighborhood

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

class VariableNeighborhoodSearch():
    def __init__(self,
                 local_search_neighborhoods: List[Neighborhood],
                 shake_neighborhoods: List[Neighborhood],
                 max_evaluations: int,
                 scaling_factor: float = 0.1):
        
        if not local_search_neighborhoods: 
            raise ValueError("A lista de vizinhanças de busca local não pode estar vazia.")
        self.history: List[Dict[str, Any]] = []
        if not shake_neighborhoods: 
            raise ValueError("A lista de vizinhanças de shake não pode estar vazia.")
            
        self.local_search_neighborhoods = local_search_neighborhoods
        self.shake_neighborhoods = shake_neighborhoods
        
        self.max_evaluations = max_evaluations
        self.scaling_factor = scaling_factor
        
        # k_max é baseado APENAS nas vizinhanças de shake
        self.k_max = len(self.shake_neighborhoods) 
        
        self.evaluations = 0
        self.best_solution: Optional[Solution] = None

    def _calculate_iterations(self, n: int, base_intensity: int) -> int:
        calculated_iters = int(n * self.scaling_factor * base_intensity)
        return max(1, calculated_iters)

    def local_search(self, solution: Solution) -> Solution:
        """
        Implementa uma RVND (Randomized Variable Neighborhood Descent).
        """
        current_solution = solution
        n = current_solution.dados.n
        
        MAX_TRIES_PER_OPERATOR = max(20, n) # Tenta pelo menos 20x, ou n vezes
        
        k_local = 0
        
        while k_local < len(self.local_search_neighborhoods) and self.evaluations < self.max_evaluations:
            
            neighborhood = self.local_search_neighborhoods[k_local]
            improvement_found_with_this_op = False
            
            for _ in range(MAX_TRIES_PER_OPERATOR):
                
                if self.evaluations >= self.max_evaluations:
                    break 
                    
                iterations_to_apply = 1 
                neighbor = neighborhood.apply(current_solution, iterations=iterations_to_apply)
                self.evaluations += iterations_to_apply
                
                neighbor.validate()
                
                if neighbor.total_cost < current_solution.total_cost - 1e-9:
                    current_solution = neighbor
                    k_local = 0 
                    improvement_found_with_this_op = True
                    break 
            
            if self.evaluations >= self.max_evaluations:
                break 

            if not improvement_found_with_this_op:
                k_local += 1
                
        return current_solution

    def shake(self, solution: Solution, k: int) -> Solution:
        """
        Aplica um SHAKE aleatório usando APENAS operadores de perturbação.
        """
        n = solution.dados.n
        
        k_effective = k % self.k_max 
        shake_operator = self.shake_neighborhoods[k_effective]
        
        iterations_to_apply = self._calculate_iterations(n, shake_operator.base_intensity)
        
        shaken_solution = shake_operator.apply(solution, iterations=iterations_to_apply)
        self.evaluations += iterations_to_apply
        
        return shaken_solution

    def solve(self, initial_solution: Solution, quiet: bool = False) -> Tuple[Optional[Solution], Dict[str, Any]]:
        start_time = time.time()
        self.evaluations = 0
        self.best_solution = None
        self.history: List[Dict[str, Any]] = [] # Reseta o histórico para esta execução
        vns_iterations = 0
        improvements_count = 0

        if not quiet:
            print(">>> Iniciando execução do VNS...")
            initial_solution.validate()
            print("\n--- Solução Inicial ---")
            print(initial_solution.summary())
            print("Executando busca local inicial...")

        # Busca local inicial
        current_solution = self.local_search(initial_solution)
        self.best_solution = current_solution
        
        if not quiet:
            valid_str = "✓ Sim" if self.best_solution.is_valid else "✗ Não"
            print(f"Custo após busca local inicial: {self.best_solution.total_cost:,.2f} (Válida: {valid_str})")

        k_max = len(self.shake_neighborhoods)
        k = 0

        # Laço principal do VNS
        while self.evaluations < self.max_evaluations:
            vns_iterations += 1
            
            entry = {
                'eval': self.evaluations,
                'vns_iter': vns_iterations,
                'k_start': k,
                'cost_current_before_shake': current_solution.total_cost,
                'is_valid_current': current_solution.is_valid,
                'phase': 'shake',
            }
            
            if not quiet:
                valid_str = "✓" if self.best_solution.is_valid else "✗"
                print(f"\rProgresso: {self.evaluations}/{self.max_evaluations} | "
                      f"Melhor: {self.best_solution.total_cost:,.2f} ({valid_str}) | "
                      f"Melhorias: {improvements_count} | k={k+1}/{k_max}", end="")

            # 1. Shake (usa a lista de shake)
            shaken_solution = self.shake(current_solution, k)
            if self.evaluations >= self.max_evaluations:
                break
            
            entry['cost_shaken'] = shaken_solution.total_cost
            entry['is_valid_shaken'] = shaken_solution.is_valid 

            # 2. Busca Local (usa a lista de busca local)
            local_optimum = self.local_search(shaken_solution)
            if self.evaluations >= self.max_evaluations:
                break
            
            entry['cost_local_optimum'] = local_optimum.total_cost
            entry['is_valid_local_optimum'] = local_optimum.is_valid

            # Critério de Aceitação
            if local_optimum.total_cost < current_solution.total_cost - 1e-9:
                entry['decision'] = 'Accepted_Reset_K'
                entry['new_k'] = 0
                current_solution = local_optimum
                k = 0
                
                if (current_solution.is_valid and 
                    current_solution.total_cost < self.best_solution.total_cost - 1e-9):
                    self.best_solution = current_solution
                    improvements_count += 1
                    if not quiet:
                        valid_str = "✓ Sim" if self.best_solution.is_valid else "✗ Não"
                        print(f"\n✨ NOVA MELHOR SOLUÇÃO (VNS): {self.best_solution.total_cost:,.2f} "
                              f"(Válida: {valid_str}) (Avaliação {self.evaluations})")
            else:
                entry['decision'] = 'Rejected_Increment_K'
                entry['new_k'] = k + 1
                k += 1
                if k >= k_max:
                    k = 0
            
            vns_iterations += 1
            self.history.append(entry)

        runtime = time.time() - start_time
        if not quiet:
            print(f"\n\n>>> Execução VNS finalizada em {runtime:.2f} segundos.")
        
        if self.best_solution:
            self.best_solution.validate()

        stats = {
            'algorithm': 'VNS',
            'runtime': runtime,
            'evaluations': self.evaluations,
            'vns_iterations': vns_iterations,
            'improvements': improvements_count,
            'final_cost': self.best_solution.total_cost if self.best_solution else None,
            'final_distance': self.best_solution.total_distance if self.best_solution else None,
            'is_valid': self.best_solution.is_valid if self.best_solution else False,
        }
        
        return self.best_solution, stats