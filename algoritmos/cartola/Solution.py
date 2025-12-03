import numpy as np
import copy
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class TripMetrics:
    route: List[int]
    cost: float
    times: List[float]
    distance: float
    duration: float
    tardiness: float
    overtime: float

@dataclass
class InsertionMove:
    cost_delta: float
    bus_idx: int
    trip_idx: Optional[int]
    new_metrics: TripMetrics
    is_new_trip: bool = False

class Solution:
    def __init__(self, num_buses: int, dados, penalty_weights: Dict[str, float]):
        self.dados = dados
        self.penalty_weights = penalty_weights
        self.routes: List[List[List[int]]] = [[] for _ in range(num_buses)]
        self.times: List[List[List[float]]] = [[] for _ in range(num_buses)]
        self.trip_distances: List[List[float]] = [[] for _ in range(num_buses)]
        self.trip_durations: List[List[float]] = [[] for _ in range(num_buses)]
        self.trip_tardiness: List[List[float]] = [[] for _ in range(num_buses)]
        self.trip_overtimes: List[List[float]] = [[] for _ in range(num_buses)]
        self.total_cost: float = 0.0
        self.total_distance: float = 0.0
        self.is_valid: bool = False
        self.violations: Dict[str, Any] = {}

    def build_initial_solution(self, seed: int = 0):
        """
        Constrói solução inicial usando uma heurística semi-aleatória (GRASP).
        Em vez de inserir na ordem 100% gulosa (EDD), ele cria uma
        Lista de Candidatos Restrita (RCL) com as 'melhores' requisições
        e seleciona uma ALEATORIAMENTE da RCL para inserir.
        """
        rng = np.random.default_rng(seed)
        n = self.dados.n

        # 1. Começa com todas as requisições "na piscina"
        requests_pool = list(range(1, n + 1))
        
        while requests_pool:
            # 2. Ordena as requisições *restantes* por prazo (EDD)
            requests_pool.sort(key=lambda i: float(self.dados.l[i-1]))
            
            # 3. Define o tamanho da RCL (ex: top 5, ou 15% das restantes)
            #    Este 'alpha' (0.15) é um bom parâmetro para ajustar
            rcl_alpha = 0.15
            rcl_size = max(1, min(5, int(len(requests_pool) * rcl_alpha)))
            
            # 4. Pega a RCL (as 'rcl_size' primeiras da lista ordenada)
            rcl = requests_pool[:rcl_size]
            
            # 5. Seleciona uma requisição ALEATORIAMENTE da RCL
            req = rcl[rng.integers(0, len(rcl))]
            
            # 6. Remove a requisição selecionada da piscina
            requests_pool.remove(req)

            best_insertion = None
            best_new_trip = None
            
            # PRIORIDADE 1: Tenta inserir em viagens existentes
            for bus_idx, bus_routes in enumerate(self.routes):
                for trip_idx, trip in enumerate(bus_routes):
                    # Calcula disponibilidade do ônibus no momento dessa viagem
                    if trip_idx == 0:
                        avail_time = self._get_bus_availability_at_trip(bus_idx, trip_idx)
                    else:
                        avail_time = float(self.times[bus_idx][trip_idx-1][-1])
                    
                    original_metrics = self._evaluate_trip_metrics(trip, avail_time)
                    
                    # Tenta todas as posições de inserção
                    for pos in range(1, len(trip)):
                        new_route = trip[:pos] + [req] + trip[pos:]
                        new_metrics = self._evaluate_trip_metrics(new_route, avail_time)
                        cost_delta = new_metrics.cost - original_metrics.cost
                        
                        move = InsertionMove(cost_delta, bus_idx, trip_idx, new_metrics, False)
                        
                        if best_insertion is None or self._is_better_move(move, best_insertion):
                            best_insertion = move
            
            # PRIORIDADE 2: Tenta criar nova viagem (com PENALIZAÇÃO)
            bus_trip_counts = [(i, len(self.routes[i])) for i in range(self.dados.K)]
            bus_trip_counts.sort(key=lambda x: (x[1], self._get_bus_availability_at_trip(x[0], x[1])))
            
            for bus_idx, num_trips in bus_trip_counts:
                if num_trips < self.dados.r:
                    avail_time = self._get_bus_availability_at_trip(bus_idx, num_trips)
                    new_route = [0, req, 0]
                    metrics = self._evaluate_trip_metrics(new_route, avail_time)
                    
                    # PENALIZA criação de nova viagem para forçar consolidação
                    penalized_cost = metrics.cost * 1.5  # 50% mais caro criar nova viagem
                    move = InsertionMove(penalized_cost, bus_idx, None, metrics, True)
                    
                    if best_new_trip is None:
                        best_new_trip = move
                    elif self._is_better_new_trip_move(move, best_new_trip):
                        best_new_trip = move
            
            # Seleciona o melhor movimento (inserção será preferida por causa da penalização)
            final_move = self._select_best_move_with_consolidation(best_insertion, best_new_trip)

            if final_move:
                self._apply_move(final_move)
            else:
                # Isso não deveria acontecer se a criação de nova viagem for sempre possível
                # print(f"⚠️ ERRO: Não foi possível inserir requisição {req}")
                pass
        
        # Recalcula e finaliza
        self.recalculate_all()
        self._calculate_final_metrics()

    def _select_best_move_with_consolidation(self, insertion: Optional[InsertionMove], 
                                             new_trip: Optional[InsertionMove]) -> Optional[InsertionMove]:
        """Seleciona movimento PRIORIZANDO consolidação (inserção sobre nova viagem)."""
        if not insertion and not new_trip:
            return None
        
        if not insertion:
            return new_trip
        if not new_trip:
            return insertion
        
        # Verifica factibilidade
        ins_valid = (insertion.new_metrics.overtime < 1e-9 and 
                     insertion.new_metrics.tardiness < 1e-9)
        new_valid = (new_trip.new_metrics.overtime < 1e-9 and 
                     new_trip.new_metrics.tardiness < 1e-9)
        
        # PRIORIDADE 1: Factibilidade
        if ins_valid and not new_valid:
            return insertion
        if new_valid and not ins_valid:
            return new_trip
        
        # PRIORIDADE 2: Se ambos válidos, PREFERE INSERÇÃO (consolidação)
        if ins_valid and new_valid:
            # Compara custo considerando a penalização da nova viagem
            return insertion if insertion.cost_delta < new_trip.cost_delta else new_trip
        
        # Ambos inválidos: menor violação
        ins_violation = (insertion.new_metrics.overtime + insertion.new_metrics.tardiness)
        new_violation = (new_trip.new_metrics.overtime + new_trip.new_metrics.tardiness)
        
        return insertion if ins_violation < new_violation else new_trip

    def _is_better_new_trip_move(self, move1: InsertionMove, move2: InsertionMove) -> bool:
        """Compara movimentos de NOVA VIAGEM, priorizando BALANCEAMENTO."""
        # Obtém quantas viagens cada ônibus já tem
        bus1_trips = len(self.routes[move1.bus_idx])
        bus2_trips = len(self.routes[move2.bus_idx])
        
        # PRIORIDADE 1: Balanceamento - prefere ônibus com MENOS viagens
        if bus1_trips < bus2_trips:
            return True
        if bus2_trips < bus1_trips:
            return False
        
        # PRIORIDADE 2: Factibilidade
        valid1 = (move1.new_metrics.overtime < 1e-9 and move1.new_metrics.tardiness < 1e-9)
        valid2 = (move2.new_metrics.overtime < 1e-9 and move2.new_metrics.tardiness < 1e-9)
        
        if valid1 and not valid2:
            return True
        if valid2 and not valid1:
            return False
        
        # PRIORIDADE 3: Menor custo
        return move1.new_metrics.cost < move2.new_metrics.cost

    def _get_bus_availability_at_trip(self, bus_idx: int, trip_idx: int) -> float:
        """Retorna quando o ônibus estará disponível para uma viagem específica."""
        if trip_idx == 0:
            return 0.0  # Primeira viagem: disponível no tempo 0
        elif trip_idx <= len(self.times[bus_idx]) and self.times[bus_idx]:
            # Retorna o tempo de fim da última viagem já calculada
            return float(self.times[bus_idx][-1][-1])
        else:
            return 0.0

    def _select_best_move_with_consolidation(self, insertion: Optional[InsertionMove], 
                                             new_trip: Optional[InsertionMove]) -> Optional[InsertionMove]:
        """Seleciona movimento PRIORIZANDO consolidação (inserção sobre nova viagem)."""
        if not insertion and not new_trip:
            return None
        
        if not insertion:
            return new_trip
        if not new_trip:
            return insertion
        
        # Verifica factibilidade
        ins_valid = (insertion.new_metrics.overtime < 1e-9 and 
                     insertion.new_metrics.tardiness < 1e-9)
        new_valid = (new_trip.new_metrics.overtime < 1e-9 and 
                     new_trip.new_metrics.tardiness < 1e-9)
        
        # PRIORIDADE 1: Factibilidade
        if ins_valid and not new_valid:
            return insertion
        if new_valid and not ins_valid:
            return new_trip
        
        # PRIORIDADE 2: Se ambos válidos, PREFERE INSERÇÃO (consolidação)
        if ins_valid and new_valid:
            # Compara custo considerando a penalização da nova viagem
            return insertion if insertion.cost_delta < new_trip.cost_delta else new_trip
        
        # Ambos inválidos: menor violação
        ins_violation = (insertion.new_metrics.overtime + insertion.new_metrics.tardiness)
        new_violation = (new_trip.new_metrics.overtime + new_trip.new_metrics.tardiness)
        
        return insertion if ins_violation < new_violation else new_trip

    def _is_better_move(self, move1: InsertionMove, move2: InsertionMove) -> bool:
        """Compara dois movimentos priorizando factibilidade."""
        metrics1 = move1.new_metrics
        metrics2 = move2.new_metrics
        
        # Verifica factibilidade
        valid1 = (metrics1.overtime < 1e-9 and metrics1.tardiness < 1e-9)
        valid2 = (metrics2.overtime < 1e-9 and metrics2.tardiness < 1e-9)
        
        if valid1 and not valid2:
            return True  # Move1 é válido, move2 não
        if valid2 and not valid1:
            return False  # Move2 é válido, move1 não
        
        # Ambos válidos ou ambos inválidos: compara custo
        cost1 = move1.cost_delta if not move1.is_new_trip else metrics1.cost
        cost2 = move2.cost_delta if not move2.is_new_trip else metrics2.cost
        
        return cost1 < cost2

    def _select_best_move(self, insertion: Optional[InsertionMove], 
                         new_trip: Optional[InsertionMove]) -> Optional[InsertionMove]:
        """Seleciona melhor movimento PRIORIZANDO FORTEMENTE factibilidade."""
        if not insertion and not new_trip:
            return None
        
        if not insertion:
            return new_trip
        if not new_trip:
            return insertion
        
        # Verifica factibilidade
        ins_valid = (insertion.new_metrics.overtime < 1e-9 and 
                     insertion.new_metrics.tardiness < 1e-9)
        new_valid = (new_trip.new_metrics.overtime < 1e-9 and 
                     new_trip.new_metrics.tardiness < 1e-9)
        
        # PRIORIDADE MÁXIMA: Factibilidade
        if ins_valid and not new_valid:
            return insertion
        if new_valid and not ins_valid:
            return new_trip
        
        # Ambos válidos: PREFERÊNCIA por nova viagem se balancear melhor
        if ins_valid and new_valid:
            # Verifica o balanceamento: se nova viagem for em ônibus com poucas viagens, prefere
            new_trip_bus_count = len(self.routes[new_trip.bus_idx])
            ins_bus_count = len(self.routes[insertion.bus_idx])
            
            # Se nova viagem é em ônibus com METADE ou menos viagens, prefere (balanceamento)
            max_bus_count = max(len(routes) for routes in self.routes)
            if new_trip_bus_count < max_bus_count * 0.7:
                return new_trip
            
            # Caso contrário, compara custo real
            ins_real_cost = insertion.new_metrics.cost
            new_real_cost = new_trip.new_metrics.cost
            return insertion if ins_real_cost < new_real_cost else new_trip
        
        # Ambos inválidos: escolhe o com MENOR VIOLAÇÃO (não menor custo!)
        ins_violation = (insertion.new_metrics.overtime + insertion.new_metrics.tardiness)
        new_violation = (new_trip.new_metrics.overtime + new_trip.new_metrics.tardiness)
        
        if abs(ins_violation - new_violation) < 1e-6:
            # Violações similares: prefere nova viagem se balancear
            new_trip_bus_count = len(self.routes[new_trip.bus_idx])
            max_bus_count = max(len(routes) for routes in self.routes)
            if new_trip_bus_count < max_bus_count * 0.7:
                return new_trip
            
            # Desempata por custo
            ins_real_cost = insertion.new_metrics.cost
            new_real_cost = new_trip.new_metrics.cost
            return insertion if ins_real_cost < new_real_cost else new_trip
        
        return insertion if ins_violation < new_violation else new_trip

    def _apply_move(self, move: InsertionMove):
        """Aplica movimento e atualiza estruturas."""
        bus_idx, trip_idx, metrics = move.bus_idx, move.trip_idx, move.new_metrics
        
        if trip_idx is None:  # Nova viagem
            self.routes[bus_idx].append(metrics.route)
            self.times[bus_idx].append(metrics.times)
            self.trip_distances[bus_idx].append(metrics.distance)
            self.trip_durations[bus_idx].append(metrics.duration)
            self.trip_tardiness[bus_idx].append(metrics.tardiness)
            self.trip_overtimes[bus_idx].append(metrics.overtime)
        else:  # Atualiza viagem existente
            self.routes[bus_idx][trip_idx] = metrics.route
            self.times[bus_idx][trip_idx] = metrics.times
            self.trip_distances[bus_idx][trip_idx] = metrics.distance
            self.trip_durations[bus_idx][trip_idx] = metrics.duration
            self.trip_tardiness[bus_idx][trip_idx] = metrics.tardiness
            self.trip_overtimes[bus_idx][trip_idx] = metrics.overtime

    def recalculate_all(self):
        """Recalcula todas as métricas e REMOVE VIAGENS VAZIAS."""
        num_buses = len(self.routes)
        self.times = [[] for _ in range(num_buses)]
        self.trip_distances = [[] for _ in range(num_buses)]
        self.trip_durations = [[] for _ in range(num_buses)]
        self.trip_tardiness = [[] for _ in range(num_buses)]
        self.trip_overtimes = [[] for _ in range(num_buses)]

        for bus_idx in range(num_buses):
            # Remove viagens vazias ou inválidas
            valid_trips = []
            for trip in self.routes[bus_idx]:
                # Mantém apenas viagens com pelo menos uma requisição
                if len(trip) >= 3 and any(req != 0 for req in trip):
                    valid_trips.append(trip)
            
            self.routes[bus_idx] = valid_trips
            last_trip_end_time = 0.0
            
            for trip_route in self.routes[bus_idx]:
                metrics = self._evaluate_trip_metrics(trip_route, last_trip_end_time)
                self.times[bus_idx].append(metrics.times)
                self.trip_distances[bus_idx].append(metrics.distance)
                self.trip_durations[bus_idx].append(metrics.duration)
                self.trip_tardiness[bus_idx].append(metrics.tardiness)
                self.trip_overtimes[bus_idx].append(metrics.overtime)
                last_trip_end_time = metrics.times[-1]
        
        self._calculate_final_metrics()

    def _evaluate_trip_metrics(self, trip: List[int], bus_available_time: float = 0.0) -> TripMetrics:
        """Calcula métricas para uma viagem."""
        b, duration = self._schedule_trip(trip, bus_available_time)
        distance = self._get_trip_distance(trip)
        tardiness = self._get_trip_tardiness(trip, b)
        overtime = self._get_trip_overtime(duration)
        cost = (distance + 
                self.penalty_weights['lambda_tw'] * tardiness + 
                self.penalty_weights['lambda_tmax'] * overtime)
        return TripMetrics(trip, cost, b, distance, duration, tardiness, overtime)

    def _schedule_trip(self, trip: List[int], bus_available_time: float = 0.0) -> Tuple[List[float], float]:
        """Agenda horários de uma viagem."""
        if len(trip) < 3:
            s0 = float(self.dados.s[0])
            b = [bus_available_time, bus_available_time + s0]
            return b, s0
        
        b = [0.0] * len(trip)
        first_request = trip[1]
        travel_time_to_first = float(self.dados.s[0]) + float(self.dados.T[0, first_request])
        earliest_window = float(self.dados.e[first_request - 1])
        naive_optimal_start = max(0.0, earliest_window - travel_time_to_first)
        optimal_start = max(bus_available_time, naive_optimal_start)
        
        b[0] = optimal_start
        departure_time = optimal_start + float(self.dados.s[0])
        current_time = departure_time
        
        for idx in range(1, len(trip) - 1):
            prev_node, current_node = trip[idx-1], trip[idx]
            if prev_node == 0:
                arrival_time = departure_time + float(self.dados.T[0, current_node])
            else:
                arrival_time = (current_time + 
                              float(self.dados.s[prev_node]) + 
                              float(self.dados.T[prev_node, current_node]))
            start_time = max(arrival_time, float(self.dados.e[current_node-1]))
            b[idx] = start_time
            current_time = start_time
        
        last_request_node = trip[-2]
        arrival_at_depot = (current_time + 
                          float(self.dados.s[last_request_node]) + 
                          float(self.dados.T[last_request_node, 0]))
        b[-1] = arrival_at_depot
        trip_duration = arrival_at_depot - b[0]
        
        return b, trip_duration

    def _get_trip_distance(self, trip: List[int]) -> float:
        return sum(float(self.dados.D[a, b]) for a, b in zip(trip[:-1], trip[1:]))

    def _get_trip_tardiness(self, trip: List[int], b: List[float]) -> float:
        return sum(max(0.0, b_i - float(self.dados.l[i-1])) 
                  for i, b_i in zip(trip, b) if i != 0)

    def _get_trip_overtime(self, duration: float) -> float:
        tmax = self.penalty_weights.get('tmax')
        return max(0.0, duration - tmax) if tmax else 0.0

    def _calculate_final_metrics(self):
        """Calcula métricas agregadas."""
        self.total_distance = sum(d for bus_dists in self.trip_distances for d in bus_dists)
        total_tard = sum(t for bus_tards in self.trip_tardiness for t in bus_tards)
        total_over = sum(o for bus_overs in self.trip_overtimes for o in bus_overs)
        self.total_cost = (self.total_distance + 
                          self.penalty_weights['lambda_tw'] * total_tard + 
                          self.penalty_weights['lambda_tmax'] * total_over)

    def validate(self) -> bool:
        """Valida a solução."""
        self.violations = {}
        
        total_tardiness = sum(t for bus_tards in self.trip_tardiness for t in bus_tards)
        if total_tardiness > 1e-9:
            self.violations['time_windows'] = f"Atraso total de {total_tardiness:.2f}"
        
        total_overtime = sum(o for bus_overs in self.trip_overtimes for o in bus_overs)
        if total_overtime > 1e-9:
            self.violations['max_duration'] = f"Tempo extra total de {total_overtime:.2f}"
        
        all_requests = [req for bus in self.routes for trip in bus for req in trip if req != 0]
        expected = set(range(1, self.dados.n + 1))
        actual = set(all_requests)
        
        missing = list(expected - actual)
        if missing:
            self.violations['coverage_missing'] = sorted(missing)
        
        if len(all_requests) != len(actual):
            counts = {req: all_requests.count(req) for req in actual}
            duplicates = [req for req, count in counts.items() if count > 1]
            self.violations['coverage_duplicates'] = sorted(duplicates)
        
        for bus_idx, bus_routes in enumerate(self.routes):
            for trip_idx, trip in enumerate(bus_routes):
                if len(trip) > 1 and (trip[0] != 0 or trip[-1] != 0):
                    self.violations.setdefault('structure', []).append((bus_idx, trip_idx))
        
        self.is_valid = not bool(self.violations)
        return self.is_valid

    def copy(self) -> 'Solution':
        return copy.deepcopy(self)

    def summary(self) -> str:
        lines = ["="*50, " RESUMO DA SOLUÇÃO",
                f"  - Custo Total: {self.total_cost:,.2f}",
                f"  - Distância Total: {self.total_distance:,.2f}",
                f"  - Válida: {'Sim' if self.is_valid else 'Não'}"]
        if not self.is_valid:
            lines.append(f"  - Violações: {self.violations}")
        
        for bus_idx, bus_routes in enumerate(self.routes):
            if not bus_routes: continue
            lines.append(f"\n--- Ônibus {bus_idx} ---")
            for trip_idx, trip in enumerate(bus_routes):
                dist = self.trip_distances[bus_idx][trip_idx]
                dur = self.trip_durations[bus_idx][trip_idx]
                overtime = self.trip_overtimes[bus_idx][trip_idx]
                status = "✗ OVERTIME" if overtime > 1e-9 else "✓"
                lines.append(f"  Viagem {trip_idx}: {trip} | Dist: {dist:.2f} | Dur: {dur:.1f}/{self.dados.Tmax:.0f} {status}")
        
        lines.append("="*50)
        return "\n".join(lines)