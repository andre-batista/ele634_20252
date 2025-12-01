import random
from abc import ABC, abstractmethod
from typing import Optional
from Solution import Solution

class Neighborhood(ABC):
    def __init__(self, base_intensity: int = 1):
        self.base_intensity = base_intensity
        self.name = self.__class__.__name__

    @abstractmethod
    def apply(self, solution: Solution, iterations: int) -> Solution:
        pass

    def _select_random_trip(self, solution: Solution) -> tuple[int, int] | None:
        """Seleciona viagem aleatória COM requisições."""
        active_trips = [(i, j) for i, routes in enumerate(solution.routes) 
                       for j, trip in enumerate(routes) if len(trip) >= 3]
        if not active_trips:
            return None
        return random.choice(active_trips)

    def _select_two_requests_from_trip(self, trip: list) -> tuple[int, int] | None:
        num_requests = len(trip) - 2
        if num_requests < 2:
            return None
        idx1, idx2 = random.sample(range(1, num_requests + 1), 2)
        return idx1, idx2

    def _select_one_request_from_trip(self, trip: list) -> Optional[int]:
        num_requests = len(trip) - 2
        if num_requests < 1:
            return None
        return random.randint(1, num_requests)

class SwapTripsBetweenBuses(Neighborhood):
    """Troca viagens inteiras entre ônibus."""
    def apply(self, solution: Solution, iterations: int) -> Solution:
        solution_copy = solution.copy()
        applied_count = 0
        max_attempts = iterations * 10

        while applied_count < iterations and max_attempts > 0:
            max_attempts -= 1
            
            indices1 = self._select_random_trip(solution_copy)
            if not indices1:
                continue
            bus1_idx, trip1_idx = indices1
            
            indices2 = self._select_random_trip(solution_copy)
            if not indices2:
                continue
            bus2_idx, trip2_idx = indices2
            
            if bus1_idx == bus2_idx:
                continue
            
            trip1 = solution_copy.routes[bus1_idx][trip1_idx]
            trip2 = solution_copy.routes[bus2_idx][trip2_idx]
            
            solution_copy.routes[bus1_idx][trip1_idx] = trip2
            solution_copy.routes[bus2_idx][trip2_idx] = trip1
            
            applied_count += 1

        if applied_count > 0:
            solution_copy.recalculate_all()
        return solution_copy
    
class RemoveAndReinsert(Neighborhood):
    """Remove requisição e testa ALGUMAS posições (não todas)."""
    def apply(self, solution: Solution, iterations: int) -> Solution:
        solution_copy = solution.copy()
        applied_count = 0
        max_attempts = iterations * 10
        
        while applied_count < iterations and max_attempts > 0:
            max_attempts -= 1
            
            # 1. Remove requisição de viagem aleatória
            indices_from = self._select_random_trip(solution_copy)
            if not indices_from:
                continue
            
            bus_from, trip_from = indices_from
            trip = solution_copy.routes[bus_from][trip_from]
            
            if len(trip) <= 3:
                continue
            
            req_idx = self._select_one_request_from_trip(trip)
            if req_idx is None:
                continue
            
            # 2. Seleciona APENAS algumas viagens candidatas (não todas)
            num_trips_to_test = min(5, sum(len(routes) for routes in solution_copy.routes))
            candidate_trips = []
            
            for bus_idx, bus_routes in enumerate(solution_copy.routes):
                for trip_idx, _ in enumerate(bus_routes):
                    if not (bus_idx == bus_from and trip_idx == trip_from):
                        candidate_trips.append((bus_idx, trip_idx))
            
            if not candidate_trips:
                continue
            
            # Testa apenas algumas viagens aleatórias
            selected_trips = random.sample(candidate_trips, 
                                          min(num_trips_to_test, len(candidate_trips)))
            
            # 3. Para cada viagem candidata, testa POUCAS posições
            best_move = None
            best_cost = solution_copy.total_cost
            
            for bus_to, trip_to in selected_trips:
                target_trip = solution_copy.routes[bus_to][trip_to]
                
                # Testa apenas 2-3 posições por viagem
                num_positions = min(3, len(target_trip) - 1)
                if num_positions <= 0:
                    continue
                
                positions = random.sample(range(1, len(target_trip)), num_positions)
                
                for pos in positions:
                    # Avalia movimento SEM copiar solução inteira
                    removed_req = trip[req_idx]
                    
                    # Estimativa rápida de custo (sem recalcular tudo)
                    delta_cost = self._estimate_insertion_cost(
                        solution_copy, bus_from, trip_from, req_idx,
                        bus_to, trip_to, pos
                    )
                    
                    new_cost = solution_copy.total_cost + delta_cost
                    
                    if new_cost < best_cost:
                        best_cost = new_cost
                        best_move = (bus_to, trip_to, pos)
            
            # 4. Aplica melhor movimento encontrado
            if best_move:
                bus_to, trip_to, pos = best_move
                removed = solution_copy.routes[bus_from][trip_from].pop(req_idx)
                solution_copy.routes[bus_to][trip_to].insert(pos, removed)
                applied_count += 1
        
        if applied_count > 0:
            solution_copy.recalculate_all()  # Recalcula UMA VEZ no final
        
        return solution_copy
    
    def _estimate_insertion_cost(self, sol, bus_from, trip_from, req_idx, bus_to, trip_to, insert_pos):
        """Estimativa RÁPIDA sem recalcular tudo."""
        # Custo de remover da viagem original
        trip_from_route = sol.routes[bus_from][trip_from]
        if req_idx > 0 and req_idx < len(trip_from_route) - 1:
            prev = trip_from_route[req_idx - 1]
            curr = trip_from_route[req_idx]
            next = trip_from_route[req_idx + 1]
            
            cost_removed = -(float(sol.dados.D[prev, curr]) + 
                           float(sol.dados.D[curr, next]) - 
                           float(sol.dados.D[prev, next]))
        else:
            cost_removed = 0
        
        # Custo de inserir na viagem destino
        trip_to_route = sol.routes[bus_to][trip_to]
        if insert_pos < len(trip_to_route):
            prev_to = trip_to_route[insert_pos - 1]
            next_to = trip_to_route[insert_pos]
            req = trip_from_route[req_idx]
            
            cost_added = (float(sol.dados.D[prev_to, req]) + 
                         float(sol.dados.D[req, next_to]) - 
                         float(sol.dados.D[prev_to, next_to]))
        else:
            cost_added = 0
        
        return cost_removed + cost_added
    
class MergeTrips(Neighborhood):
    """(SHAKE) Tenta fundir duas viagens ALEATÓRIAS."""
    def apply(self, solution: Solution, iterations: int) -> Solution:
        solution_copy = solution.copy()
        applied_count = 0
        # Tenta mais vezes, pois muitas combinações aleatórias podem ser ruins
        max_attempts = iterations * 10 
        
        while applied_count < iterations and max_attempts > 0:
            max_attempts -= 1
            
            # 1. Coleta TODAS as viagens ativas
            all_trips = []
            for bus_idx, bus_routes in enumerate(solution_copy.routes):
                for trip_idx, trip in enumerate(bus_routes):
                    if len(trip) >= 3: # Ignora viagens já vazias
                        all_trips.append((bus_idx, trip_idx))
            
            if len(all_trips) < 2:
                break # Não há o que fundir

            # 2. Pega duas viagens ALEATÓRIAS da lista
            try:
                # Pega os ÍNDICES da lista 'all_trips'
                idx1, idx2 = random.sample(range(len(all_trips)), 2)
                (bus1, t1_idx) = all_trips[idx1]
                (bus2, t2_idx) = all_trips[idx2]
                
                trip1 = solution_copy.routes[bus1][t1_idx]
                trip2 = solution_copy.routes[bus2][t2_idx]
            except (IndexError, ValueError):
                continue # Falha se as listas mudaram, tenta de novo

            # 3. Aplica o merge (t2 é fundida no final de t1)
            merged_trip = trip1[:-1] + trip2[1:]
            
            # 4. Atualiza a solução
            solution_copy.routes[bus1][t1_idx] = merged_trip
            solution_copy.routes[bus2][t2_idx] = [] # Esvazia a viagem 2
            
            # Remove a viagem fundida da lista para a próxima iteração
            # (Remove o de índice maior primeiro para não bagunçar os índices)
            all_trips.pop(max(idx1, idx2))
            all_trips.pop(min(idx1, idx2))
            
            applied_count += 1
        
        if applied_count > 0:
            # Recalcula UMA VEZ no final para limpar as viagens vazias ([])
            solution_copy.recalculate_all()
        
        return solution_copy

class SplitTrip(Neighborhood):
    """(SHAKE) Divide uma viagem longa em um ponto ALEATÓRIO."""
    def apply(self, solution: Solution, iterations: int) -> Solution:
        solution_copy = solution.copy()
        applied_count = 0
        max_attempts = iterations * 5
        
        while applied_count < iterations and max_attempts > 0:
            max_attempts -= 1
            
            # 1. Seleciona viagens LONGAS (candidatas a split)
            candidate_trips = []
            for bus_idx, bus_routes in enumerate(solution_copy.routes):
                # O ônibus pode aceitar mais uma viagem?
                if len(bus_routes) >= solution_copy.dados.r:
                    continue  # Ônibus já no limite
                
                for trip_idx, trip in enumerate(bus_routes):
                    # Pode ser dividida? Precisa de pelo menos 4 reqs [0, A, B, C, D, 0] (len=6)
                    # para virar [0, A, B, 0] e [0, C, D, 0]
                    if len(trip) >= 6: 
                        candidate_trips.append((bus_idx, trip_idx))
            
            if not candidate_trips:
                continue # Nenhuma viagem longa o suficiente encontrada
            
            # 2. Pega uma viagem candidata ALEATORIAMENTE (NÃO a mais longa)
            bus_idx, t_idx = random.choice(candidate_trips)
            trip = solution_copy.routes[bus_idx][t_idx]
            
            # 3. Define um ponto de divisão ALEATÓRIO
            # Ex: [0, 1, 2, 3, 4, 0], len=6. 
            # Pontos de split válidos: 2, 3, 4
            # min_split_idx = 2 (garante [0, 1, 0])
            # max_split_idx = len(trip) - 2 (garante [0, 3, 4, 0])
            
            min_idx = 2 
            max_idx = len(trip) - 2
            
            if min_idx >= max_idx:
                continue # Viagem não pode ser dividida
                
            split_point = random.randint(min_idx, max_idx)
            
            # 4. Aplica a divisão
            trip1 = trip[:split_point] + [0]
            trip2 = [0] + trip[split_point:]
            
            solution_copy.routes[bus_idx][t_idx] = trip1
            solution_copy.routes[bus_idx].append(trip2) # Adiciona a nova viagem
            applied_count += 1
        
        if applied_count > 0:
            solution_copy.recalculate_all()
        
        return solution_copy

class TwoOpt(Neighborhood):
    """2-opt clássico: remove cruzamentos na rota."""
    def apply(self, solution: Solution, iterations: int) -> Solution:
        solution_copy = solution.copy()
        applied_count = 0
        max_attempts = iterations * 5
        
        while applied_count < iterations and max_attempts > 0:
            max_attempts -= 1
            
            trip_idx = self._select_random_trip(solution_copy)
            if not trip_idx:
                continue
            
            bus_idx, t_idx = trip_idx
            trip = solution_copy.routes[bus_idx][t_idx]
            
            if len(trip) < 4:
                continue
            
            # Seleciona dois pontos de corte
            i = random.randint(1, len(trip) - 3)
            j = random.randint(i + 1, len(trip) - 2)
            
            # Inverte segmento entre i e j
            trip[i:j+1] = reversed(trip[i:j+1])
            applied_count += 1
        
        if applied_count > 0:
            solution_copy.recalculate_all()
        
        return solution_copy