# src/core/solution.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from .instance import Instance

@dataclass
class Solution:
    inst: Instance
    routes: Dict[int, List[List[int]]] = field(default_factory=dict)

    # ---------- construção básica ----------
    @classmethod
    def new_empty(cls, inst: Instance) -> "Solution":
        return cls(inst=inst, routes={k: [] for k in range(inst.K)})

    def start_new_trip(self, vehicle: int):
        self.routes[vehicle].append([0])

    def finish_current_trip(self, vehicle: int):
        trip = self.routes[vehicle][-1]
        if trip[-1] != 0:
            trip.append(0)
        elif len(trip) == 1:
            trip.append(0)

    def add_stop_current_trip(self, vehicle: int, node: int):
        trip = self.routes[vehicle][-1]
        if trip and trip[-1] == 0 and len(trip) > 1:
            raise ValueError("Viagem já encerrada (0 no final).")
        trip.append(node)

    # ---------- métricas ----------
    def total_cost(self) -> float:
        c = self.inst.c
        total = 0.0
        for k in self.routes:
            for trip in self.routes[k]:
                for i, j in zip(trip, trip[1:]):
                    total += c[i][j]
        return total

    def trip_times(self) -> List[float]:
        T = self.inst.T
        times = []
        for k in self.routes:
            for trip in self.routes[k]:
                t = 0.0
                for i, j in zip(trip, trip[1:]):
                    t += T[i][j]
                times.append(t)
        return times

    def trip_cost(self, trip: List[int]) -> float:
        c = 0.0
        for i, j in zip(trip, trip[1:]):
            c += self.arc_cost(i, j)
        return c

    def pretty(self) -> str:
        lines = ["=== SOLUÇÃO ==="]
        for k in range(self.inst.K):
            lines.append(f"Veículo {k}:")
            if not self.routes[k]:
                lines.append("  (sem viagens)")
            else:
                for idx, trip in enumerate(self.routes[k], 1):
                    lines.append(f"  Viagem {idx}: " + " -> ".join(map(str, trip)))
        lines.append(f"Custo total: {self.total_cost():.2f}")
        return "\n".join(lines)

    # ---------- tempos / Tmax ----------
    def compute_trip_time(self, trip: List[int], depot_service_zero: bool = True) -> float:
        T = self.inst.T
        s = self.inst.s
        total = 0.0
        for i, j in zip(trip, trip[1:]):
            total += T[i][j]
        for node in trip[1:-1]:
            total += s[node]
        if not depot_service_zero:
            if trip and trip[0] == 0:
                total += s[0]
            if trip and trip[-1] == 0:
                total += s[0]
        return total

    def trip_respects_Tmax(self, trip: List[int]) -> bool:
        return self.compute_trip_time(trip) <= self.inst.Tmax + 1e-9

    def compute_arrival_times(self, trip: List[int]) -> List[float]:
        T = self.inst.T
        s = self.inst.s
        start_time = 0.0
        if len(trip) >= 2 and trip[0] == 0 and trip[1] != 0:
            first_node = trip[1]
            if self.inst.e is not None:
                e_first = self.inst.e[first_node - 1]
                travel_time = T[0][first_node]
                arrival_if_leave_now = start_time + travel_time
                if arrival_if_leave_now < e_first:
                    start_time = e_first - travel_time
        times = [start_time]
        t = start_time
        for i, j in zip(trip, trip[1:]):
            t += T[i][j]
            times.append(t)
            if j != 0:
                t += s[j]
        return times

    def compute_arrival_times_from_start(self, trip: List[int], start_time: float = 0.0) -> List[float]:
        T = self.inst.T
        s = self.inst.s
        adjusted_start = start_time
        if len(trip) >= 2 and trip[0] == 0 and trip[1] != 0:
            first_node = trip[1]
            if self.inst.e is not None:
                e_first = self.inst.e[first_node - 1]
                travel_time = T[0][first_node]
                arrival_if_leave_now = start_time + travel_time
                if arrival_if_leave_now < e_first:
                    adjusted_start = e_first - travel_time
        times = [adjusted_start]
        t = adjusted_start
        for i, j in zip(trip, trip[1:]):
            t += T[i][j]
            times.append(t)
            if j != 0:
                t += s[j]
        return times

    def _respects_time_windows_with_times(self, trip: List[int], arrival_times: List[float]) -> bool:
        if self.inst.e is None or self.inst.l is None:
            return True
        for idx, node in enumerate(trip):
            if node == 0:
                continue
            B_i = arrival_times[idx]
            e_i = self.inst.e[node - 1]
            l_i = self.inst.l[node - 1]
            if B_i < e_i - 1e-9 or B_i > l_i + 1e-9:
                return False
        return True

    def respects_time_windows(self, trip: List[int]) -> bool:
        if self.inst.e is None or self.inst.l is None:
            return True
        arrival_times = self.compute_arrival_times(trip)
        return self._respects_time_windows_with_times(trip, arrival_times)

    # ---------- validações com encadeamento (Eq. 10) ----------
    def respects_time_windows_from_start(self, trip: List[int], start_time: float) -> bool:
        if self.inst.e is None or self.inst.l is None:
            return True
        arrival = self.compute_arrival_times_from_start(trip, start_time)
        return self._respects_time_windows_with_times(trip, arrival)

    def schedule_respects_time_windows_from(self, vehicle: int, start_trip_idx: int = 0) -> bool:
        if vehicle not in self.routes:
            return True
        acc = 0.0
        for v in range(start_trip_idx):
            arrival_prev = self.compute_arrival_times_from_start(self.routes[vehicle][v], acc)
            acc = arrival_prev[-1] + float(self.inst.s[0])
        for v in range(start_trip_idx, len(self.routes[vehicle])):
            trip = self.routes[vehicle][v]
            arrival = self.compute_arrival_times_from_start(trip, acc)
            if (arrival[-1] - arrival[0]) > self.inst.Tmax + 1e-9:
                return False
            if not self._respects_time_windows_with_times(trip, arrival):
                return False
            acc = arrival[-1] + float(self.inst.s[0])
        return True

    def validate_inter_trip_temporal_sequence(self) -> bool:
        for k in range(self.inst.K):
            if k not in self.routes or len(self.routes[k]) <= 1:
                continue
            trips = self.routes[k]
            acc = 0.0
            for v_idx, trip in enumerate(trips):
                if v_idx > 0:
                    acc += self.inst.s[0]
                arrival = self.compute_arrival_times_from_start(trip, acc)
                if (arrival[-1] - arrival[0]) > self.inst.Tmax + 1e-9:
                    return False
                if not self._respects_time_windows_with_times(trip, arrival):
                    return False
                acc = arrival[-1]
        return True

    # === REPOSTO: helper que o construtivo usa ===
    def get_accumulated_time_for_trip(self, vehicle: int, trip_idx: int) -> float:
        """
        Tempo acumulado no início da viagem trip_idx do veículo (Eq. 10).
        Se trip_idx == 0 ou veículo sem viagens, retorna 0.0.
        Se trip_idx > len(trips), retorna o acumulado após a última viagem existente.
        """
        if vehicle not in self.routes or trip_idx <= 0:
            return 0.0
        trips = self.routes[vehicle]
        upto = min(trip_idx, len(trips))
        acc = 0.0
        for v in range(upto):
            arrival = self.compute_arrival_times_from_start(trips[v], acc)
            acc = arrival[-1] + float(self.inst.s[0])
        return acc

    # ---------- acesso rápido a arcos ----------
    def arc_cost(self, i: int, j: int) -> float:
        return self.inst.c[i][j]

    def arc_time(self, i: int, j: int) -> float:
        return self.inst.T[i][j]

    # ---------- deltas / inserções simples ----------
    def marginal_delta_insert_end(self, trip: List[int], node: int) -> Tuple[float, float]:
        if not trip or trip[-1] != 0:
            raise ValueError("Trip deve terminar em 0.")
        u = trip[-2]
        dc = -self.arc_cost(u, 0) + self.arc_cost(u, node) + self.arc_cost(node, 0)
        dt = -self.arc_time(u, 0) + self.arc_time(u, node) + self.inst.s[node] + self.arc_time(node, 0)
        return dc, dt

    def add_stop_end_with_check(self, vehicle: int, node: int):
        trip = self.routes[vehicle][-1]
        dc, dt = self.marginal_delta_insert_end(trip, node)
        new_trip = trip[:-1] + [node, 0]
        if not self.trip_respects_Tmax(new_trip):
            raise ValueError(f"Inserção do nó {node} estoura Tmax.")
        trip[-1:] = [node, 0]
        return dc, dt

    def marginal_delta_insert_between(self, trip: List[int], pos: int, node: int) -> Tuple[float, float]:
        if pos < 0 or pos >= len(trip) - 1:
            raise IndexError("pos inválido")
        i, j = trip[pos], trip[pos + 1]
        dc = -self.arc_cost(i, j) + self.arc_cost(i, node) + self.arc_cost(node, j)
        dt = -self.arc_time(i, j) + self.arc_time(i, node) + self.inst.s[node] + self.arc_time(node, j)
        return dc, dt

    def insert_between_with_check(self, vehicle: int, pos: int, node: int):
        trip = self.routes[vehicle][-1]
        dc, dt = self.marginal_delta_insert_between(trip, pos, node)
        new_trip = trip[: pos + 1] + [node] + trip[pos + 1 :]
        if not self.trip_respects_Tmax(new_trip):
            raise ValueError(f"Inserção do nó {node} em pos {pos} estoura Tmax.")
        trip[pos + 1 : pos + 1] = [node]
        return dc, dt

    # ---------- viabilidade local (sem contexto) ----------
    def feasible_after_insert_between(self, trip: List[int], pos: int, node: int) -> bool:
        new_trip = trip[: pos + 1] + [node] + trip[pos + 1 :]
        return self.trip_respects_Tmax(new_trip) and self.respects_time_windows(new_trip)

    def feasible_after_insert_end(self, trip: List[int], node: int) -> bool:
        if not trip or trip[-1] != 0:
            return False
        new_trip = trip[:-1] + [node, 0]
        return self.trip_respects_Tmax(new_trip) and self.respects_time_windows(new_trip)

    # ---------- viabilidade com CONTEXTO (propaga Eq. 10) ----------
    def feasible_after_insert_between_ctx(self, vehicle: int, trip_idx: int, trip: List[int], pos: int, node: int) -> bool:
        new_trip = trip[:pos + 1] + [node] + trip[pos + 1:]
        if not self.trip_respects_Tmax(new_trip):
            return False
        tmp_routes = {k: [t[:] for t in v] for k, v in self.routes.items()}
        tmp_routes[vehicle][trip_idx] = new_trip
        saved = self.routes
        try:
            self.routes = tmp_routes
            return self.schedule_respects_time_windows_from(vehicle, start_trip_idx=trip_idx)
        finally:
            self.routes = saved

    def feasible_after_insert_end_ctx(self, vehicle: int, trip_idx: int, trip: List[int], node: int) -> bool:
        if not trip or trip[-1] != 0:
            return False
        new_trip = trip[:-1] + [node, 0]
        if not self.trip_respects_Tmax(new_trip):
            return False
        tmp_routes = {k: [t[:] for t in v] for k, v in self.routes.items()}
        tmp_routes[vehicle][trip_idx] = new_trip
        saved = self.routes
        try:
            self.routes = tmp_routes
            return self.schedule_respects_time_windows_from(vehicle, start_trip_idx=trip_idx)
        finally:
            self.routes = saved

    # ---------- melhor inserção na viagem ----------
    def best_insertion_in_trip(self, trip: List[int], node: int):
        best = None
        for pos in range(len(trip) - 1):
            dc, dt = self.marginal_delta_insert_between(trip, pos, node)
            if self.feasible_after_insert_between(trip, pos, node):
                cand = (pos, False, dc, dt)
                if (best is None) or (dc < best[2] - 1e-12) or (abs(dc - best[2]) <= 1e-12 and dt < best[3]):
                    best = cand
        if trip and trip[-1] == 0:
            dc, dt = self.marginal_delta_insert_end(trip, node)
            if self.feasible_after_insert_end(trip, node):
                cand = (-1, True, dc, dt)
                if (best is None) or (dc < best[2] - 1e-12) or (abs(dc - best[2]) <= 1e-12 and dt < best[3]):
                    best = cand
        return best

    def apply_best_insertion_in_trip(self, vehicle: int, node: int):
        trip = self.routes[vehicle][-1]
        best = self.best_insertion_in_trip(trip, node)
        if best is None:
            raise ValueError(f"Nó {node} inviável em todas as posições (Tmax).")
        pos, is_end, dc, dt = best
        if is_end:
            trip[-1:] = [node, 0]
        else:
            trip[pos + 1 : pos + 1] = [node]
        return best

    # ---------- suporte a viagens ----------
    def trips_count(self, vehicle: int) -> int:
        return len(self.routes.get(vehicle, []))

    def can_start_new_trip(self, vehicle: int) -> bool:
        return self.trips_count(vehicle) < self.inst.r

    def delta_new_trip(self, node: int) -> Tuple[float, float]:
        dc = self.arc_cost(0, node) + self.arc_cost(node, 0)
        dt = self.arc_time(0, node) + self.inst.s[node] + self.arc_time(node, 0)
        return dc, dt

    def feasible_new_trip(self, node: int) -> bool:
        trip = [0, node, 0]
        return self.trip_respects_Tmax(trip) and self.respects_time_windows(trip)

    # ---------- melhor inserção na frota ----------
    def best_insertion_across_fleet(self, node: int):
        best = None
        for k in range(self.inst.K):
            if self.routes[k]:
                trip = self.routes[k][-1]
                cand = self.best_insertion_in_trip(trip, node)
                if cand is not None:
                    pos, is_end, dc, dt = cand
                    opt = ("insert", k, pos, is_end, dc, dt)
                    if (best is None) or (dc < best[4] - 1e-12) or (abs(dc - best[4]) <= 1e-12 and dt < best[5]):
                        best = opt
            if self.can_start_new_trip(k) and self.feasible_new_trip(node):
                dc, dt = self.delta_new_trip(node)
                opt = ("new_trip", k, -1, True, dc, dt)
                if (best is None) or (dc < best[4] - 1e-12) or (abs(dc - best[4]) <= 1e-12 and dt < best[5]):
                    best = opt
        return best

    def apply_best_insertion_across_fleet(self, node: int):
        best = self.best_insertion_across_fleet(node)
        if best is None:
            raise ValueError(f"Nó {node} inviável na frota inteira (Tmax ou r).")
        mode, vehicle, pos, is_end, dc, dt = best
        if mode == "insert":
            self.apply_best_insertion_in_trip(vehicle, node)
        else:
            self.start_new_trip(vehicle)
            self.add_stop_current_trip(vehicle, node)
            self.finish_current_trip(vehicle)
        return best

    # ---------- helpers remoção ----------
    def _delta_remove_at(self, trip: List[int], pos: int) -> Tuple[float, float]:
        if pos <= 0 or pos >= len(trip) - 1:
            raise IndexError("pos inválido para remoção (nó interno).")
        i, node, j = trip[pos - 1], trip[pos], trip[pos + 1]
        dc = -self.arc_cost(i, node) - self.arc_cost(node, j) + self.arc_cost(i, j)
        dt = -self.arc_time(i, node) - self.inst.s[node] - self.arc_time(node, j) + self.arc_time(i, j)
        return dc, dt

    def _apply_remove_at(self, vehicle: int, trip_idx: int, pos: int) -> Tuple[int, int]:
        trip = self.routes[vehicle][trip_idx]
        if pos <= 0 or pos >= len(trip) - 1:
            raise IndexError("pos inválido para remoção.")
        del trip[pos]
        return vehicle, trip_idx

    def _best_insertion_in_specific_trip(self, trip: List[int], node: int):
        return self.best_insertion_in_trip(trip, node)

    # ---------- 2-OPT INTRA ----------
    def two_opt_intra_trip(self, vehicle: int, trip_idx: int) -> Tuple[bool, float]:
        trip = self.routes[vehicle][trip_idx]
        n = len(trip)
        if n < 4:
            return False, 0.0
        best_delta = 0.0
        best_i, best_j = -1, -1
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                delta = (
                    -self.arc_cost(trip[i-1], trip[i])
                    -self.arc_cost(trip[j], trip[j+1])
                    +self.arc_cost(trip[i-1], trip[j])
                    +self.arc_cost(trip[i], trip[j+1])
                )
                if delta < best_delta - 1e-12:
                    new_trip = trip[:i] + trip[i:j+1][::-1] + trip[j+1:]
                    if not self.trip_respects_Tmax(new_trip):
                        continue
                    tmp_routes = {k: [t[:] for t in v] for k, v in self.routes.items()}
                    tmp_routes[vehicle][trip_idx] = new_trip
                    saved = self.routes
                    try:
                        self.routes = tmp_routes
                        if self.schedule_respects_time_windows_from(vehicle, start_trip_idx=trip_idx):
                            best_delta = delta
                            best_i, best_j = i, j
                    finally:
                        self.routes = saved
        if best_i != -1:
            trip[best_i:best_j+1] = trip[best_i:best_j+1][::-1]
            return True, -best_delta
        return False, 0.0

    def relocate_intra_trip(self, vehicle: int, trip_idx: int) -> Tuple[bool, float]:
        trip = self.routes[vehicle][trip_idx]
        n = len(trip)
        if n < 5:
            return False, 0.0
        best_move = None
        for i in range(1, n - 1):
            node = trip[i]
            delta_remove = (
                -self.arc_cost(trip[i-1], trip[i])
                -self.arc_cost(trip[i], trip[i+1])
                +self.arc_cost(trip[i-1], trip[i+1])
            )
            for j in range(1, n - 1):
                if abs(j - i) <= 1:
                    continue
                if j < i:
                    delta_insert = (
                        -self.arc_cost(trip[j-1], trip[j])
                        +self.arc_cost(trip[j-1], node)
                        +self.arc_cost(node, trip[j])
                    )
                else:
                    delta_insert = (
                        -self.arc_cost(trip[j], trip[j+1])
                        +self.arc_cost(trip[j], node)
                        +self.arc_cost(node, trip[j+1])
                    )
                delta_total = delta_remove + delta_insert
                new_trip = trip[:i] + trip[i+1:]
                if j < i:
                    new_trip = new_trip[:j] + [node] + new_trip[j:]
                else:
                    new_trip = new_trip[:j] + [node] + new_trip[j:]
                if not self.trip_respects_Tmax(new_trip):
                    continue
                tmp_routes = {k: [t[:] for t in v] for k, v in self.routes.items()}
                tmp_routes[vehicle][trip_idx] = new_trip
                saved = self.routes
                try:
                    self.routes = tmp_routes
                    if self.schedule_respects_time_windows_from(vehicle, start_trip_idx=trip_idx):
                        if (best_move is None) or (delta_total < best_move[2] - 1e-12):
                            best_move = (i, j, delta_total)
                finally:
                    self.routes = saved
        if best_move is not None:
            i, j, delta = best_move
            node = trip[i]
            trip.pop(i)
            if j > i:
                j -= 1
            trip.insert(j, node)
            return True, -delta
        return False, 0.0

    def local_search_intra(self, max_iter: int = 100):
        improved = True
        it = 0
        while improved and it < max_iter:
            improved = False
            it += 1
            for k in range(self.inst.K):
                for t_idx in range(len(self.routes[k])):
                    trip = self.routes[k][t_idx]
                    if len(trip) < 4:
                        continue
                    ok, _ = self.two_opt_intra_trip(k, t_idx)
                    if ok:
                        improved = True
                        continue
                    ok, _ = self.relocate_intra_trip(k, t_idx)
                    if ok:
                        improved = True
                        continue

    # ---------- RELOCATE (inter) ----------
    def relocate_inter_once(self) -> Tuple[bool, float]:
        best_move = None  # (delta_total, src_k, src_t, pos, dst_k, dst_t, (dst_pos, is_end))
        for src_k, trips in self.routes.items():
            for src_t, trip in enumerate(trips):
                for pos in range(1, len(trip) - 1):
                    node = trip[pos]
                    rem_dc, _ = self._delta_remove_at(trip, pos)
                    new_src_trip = trip[:pos] + trip[pos + 1:]
                    if not self.trip_respects_Tmax(new_src_trip):
                        continue
                    tmp_routes_src = {k: [t[:] for t in v] for k, v in self.routes.items()}
                    tmp_routes_src[src_k][src_t] = new_src_trip
                    saved_routes = self.routes
                    try:
                        self.routes = tmp_routes_src
                        if not self.schedule_respects_time_windows_from(src_k, start_trip_idx=src_t):
                            continue
                    finally:
                        self.routes = saved_routes
                    for dst_k, dst_trips in self.routes.items():
                        for dst_t, dst_trip in enumerate(dst_trips):
                            if dst_k == src_k and dst_t == src_t:
                                continue
                            cand = self._best_insertion_in_specific_trip(dst_trip, node)
                            if cand is None:
                                continue
                            dst_pos, is_end, ins_dc, _ = cand
                            tmp_routes = {k: [t[:] for t in v] for k, v in self.routes.items()}
                            tmp_routes[src_k][src_t] = new_src_trip[:]
                            tmp_dst = dst_trip[:]
                            if is_end:
                                if tmp_dst[-1] != 0:
                                    continue
                                tmp_dst[-1:] = [node, 0]
                            else:
                                tmp_dst[dst_pos + 1:dst_pos + 1] = [node]
                            if not self.trip_respects_Tmax(tmp_dst):
                                continue
                            tmp_routes[dst_k][dst_t] = tmp_dst
                            saved = self.routes
                            try:
                                self.routes = tmp_routes
                                if (self.schedule_respects_time_windows_from(src_k, start_trip_idx=src_t) and
                                    self.schedule_respects_time_windows_from(dst_k, start_trip_idx=dst_t)):
                                    delta_total = rem_dc + ins_dc
                                    if (best_move is None) or (delta_total < best_move[0] - 1e-12):
                                        best_move = (delta_total, src_k, src_t, pos, dst_k, dst_t, (dst_pos, is_end))
                            finally:
                                self.routes = saved
        if best_move is None or best_move[0] >= -1e-12:
            return False, 0.0
        _, src_k, src_t, pos, dst_k, dst_t, (dst_pos, is_end) = best_move
        node = self.routes[src_k][src_t][pos]
        self._apply_remove_at(src_k, src_t, pos)
        trip_dst = self.routes[dst_k][dst_t]
        if is_end:
            trip_dst[-1:] = [node, 0]
        else:
            trip_dst[dst_pos + 1:dst_pos + 1] = [node]
        return True, -best_move[0]

    # ---------- EXCHANGE (inter) ----------
    def exchange_inter_once(self) -> Tuple[bool, float]:
        best = None  # (delta_total, (k1,t1,p1,n1,cand1), (k2,t2,p2,n2,cand2))
        pairs = []
        for k1, trips1 in self.routes.items():
            for t1, trip1 in enumerate(trips1):
                for p1 in range(1, len(trip1) - 1):
                    pairs.append((k1, t1, p1, trip1[p1]))
        for i in range(len(pairs)):
            k1, t1, p1, n1 = pairs[i]
            trip1 = self.routes[k1][t1]
            dc1_rem, _ = self._delta_remove_at(trip1, p1)
            new1 = trip1[:p1] + trip1[p1 + 1:]
            if not self.trip_respects_Tmax(new1):
                continue
            tmp1 = {k: [t[:] for t in v] for k, v in self.routes.items()}
            tmp1[k1][t1] = new1
            saved1 = self.routes
            try:
                self.routes = tmp1
                if not self.schedule_respects_time_windows_from(k1, start_trip_idx=t1):
                    continue
            finally:
                self.routes = saved1
            for j in range(i + 1, len(pairs)):
                k2, t2, p2, n2 = pairs[j]
                if k1 == k2 and t1 == t2:
                    continue
                trip2 = self.routes[k2][t2]
                dc2_rem, _ = self._delta_remove_at(trip2, p2)
                new2 = trip2[:p2] + trip2[p2 + 1:]
                if not self.trip_respects_Tmax(new2):
                    continue
                tmp2 = {k: [t[:] for t in v] for k, v in self.routes.items()}
                tmp2[k1][t1] = new1[:]
                tmp2[k2][t2] = new2[:]
                saved2 = self.routes
                try:
                    self.routes = tmp2
                    if not (self.schedule_respects_time_windows_from(k1, start_trip_idx=t1) and
                            self.schedule_respects_time_windows_from(k2, start_trip_idx=t2)):
                        continue
                finally:
                    self.routes = saved2

                cand2 = self._best_insertion_in_specific_trip(new2, n1)
                cand1 = self._best_insertion_in_specific_trip(new1, n2)
                if cand1 is None or cand2 is None:
                    continue

                def _apply_tmp(tr, cand, node):
                    tr_tmp = tr[:]
                    pos, end, _, _ = cand
                    if end:
                        tr_tmp[-1:] = [node, 0]
                    else:
                        tr_tmp[pos + 1:pos + 1] = [node]
                    return tr_tmp

                new2b = _apply_tmp(new2, cand2, n1)
                if not self.trip_respects_Tmax(new2b):
                    continue
                new1b = _apply_tmp(new1, cand1, n2)
                if not self.trip_respects_Tmax(new1b):
                    continue

                tmp3 = {k: [t[:] for t in v] for k, v in self.routes.items()}
                tmp3[k1][t1] = new1b[:]
                tmp3[k2][t2] = new2b[:]
                saved3 = self.routes
                try:
                    self.routes = tmp3
                    if not (self.schedule_respects_time_windows_from(k1, start_trip_idx=t1) and
                            self.schedule_respects_time_windows_from(k2, start_trip_idx=t2)):
                        continue
                    delta = (dc1_rem + dc2_rem
                             + (self.trip_cost(new1b) - self.trip_cost(new1))
                             + (self.trip_cost(new2b) - self.trip_cost(new2)))
                    if (best is None) or (delta < best[0] - 1e-12):
                        best = (delta, (k1, t1, p1, n1, cand1), (k2, t2, p2, n2, cand2))
                finally:
                    self.routes = saved3

        if best is None or best[0] >= -1e-12:
            return False, 0.0

        _, (k1, t1, p1, n1, cand1), (k2, t2, p2, n2, cand2) = best
        for (k, t, p) in sorted([(k1, t1, p1), (k2, t2, p2)], key=lambda x: (-x[0], -x[1], -x[2])):
            self._apply_remove_at(k, t, p)
        trip1 = self.routes[k1][t1]
        trip2 = self.routes[k2][t2]
        pos1, end1, _, _ = cand1
        if end1:
            trip1[-1:] = [n2, 0]
        else:
            trip1[pos1 + 1:pos1 + 1] = [n2]
        pos2, end2, _, _ = cand2
        if end2:
            trip2[-1:] = [n1, 0]
        else:
            trip2[pos2 + 1:pos2 + 1] = [n1]
        return True, -best[0]

    # ---------- MERGE e SPLIT ----------
    def merge_two_trips_if_better(self, vehicle: int, t_idx_a: int, t_idx_b: int) -> Tuple[bool, float]:
        trips = self.routes[vehicle]
        if t_idx_a < 0 or t_idx_b != t_idx_a + 1 or t_idx_b >= len(trips):
            return False, 0.0
        A = trips[t_idx_a]
        B = trips[t_idx_b]
        if len(A) < 2 or len(B) < 2:
            return False, 0.0
        u = A[-2]
        v = B[1]
        dc = -self.arc_cost(u, 0) - self.arc_cost(0, v) + self.arc_cost(u, v)
        merged = A[:-1] + B[1:]
        if not self.trip_respects_Tmax(merged):
            return False, 0.0
        tmp_routes = {k: [t[:] for t in vtr] for k, vtr in self.routes.items()}
        tmp_routes[vehicle][t_idx_a] = merged[:]
        del tmp_routes[vehicle][t_idx_b]
        saved = self.routes
        try:
            self.routes = tmp_routes
            if not self.schedule_respects_time_windows_from(vehicle, start_trip_idx=min(t_idx_a, t_idx_b-1)):
                return False, 0.0
        finally:
            self.routes = saved
        if dc >= -1e-12:
            return False, 0.0
        trips[t_idx_a] = merged
        del trips[t_idx_b]
        return True, -dc

    def split_trip_if_better(self, vehicle: int, t_idx: int) -> Tuple[bool, float]:
        trip = self.routes[vehicle][t_idx]
        best = None
        for cut in range(2, len(trip) - 2):
            A = trip[:cut] + [0]
            B = [0] + trip[cut:]
            if not (self.trip_respects_Tmax(A) and self.trip_respects_Tmax(B)):
                continue
            tmp_routes = {k: [t[:] for t in v] for k, v in self.routes.items()}
            tmp_routes[vehicle][t_idx] = A[:]
            tmp_routes[vehicle].insert(t_idx + 1, B[:])
            saved = self.routes
            try:
                self.routes = tmp_routes
                if not self.schedule_respects_time_windows_from(vehicle, start_trip_idx=t_idx):
                    continue
            finally:
                self.routes = saved
            dc = (self.trip_cost(A) + self.trip_cost(B)) - self.trip_cost(trip)
            if (best is None) or (dc < best[0] - 1e-12):
                best = (dc, A, B)
        if best is None or best[0] >= -1e-12:
            return False, 0.0
        _, A, B = best
        self.routes[vehicle][t_idx] = A
        self.routes[vehicle].insert(t_idx + 1, B)
        return True, -best[0]

    # ---------- orquestrador inter ----------
    def local_search_inter(self, allow_relocate=True, allow_exchange=True, allow_merge_split=True, max_iter=10_000):
        improved = True
        it = 0
        while improved and it < max_iter:
            it += 1
            improved = False
            if allow_relocate:
                ok, _ = self.relocate_inter_once()
                if ok:
                    improved = True
                    continue
            if allow_exchange:
                ok, _ = self.exchange_inter_once()
                if ok:
                    improved = True
                    continue
            if allow_merge_split:
                merged_or_split = False
                for k in range(self.inst.K):
                    t = 0
                    while t + 1 < len(self.routes[k]):
                        ok, _ = self.merge_two_trips_if_better(k, t, t + 1)
                        if ok:
                            merged_or_split = True
                        else:
                            t += 1
                    for t_idx in range(len(self.routes[k])):
                        ok, _ = self.split_trip_if_better(k, t_idx)
                        if ok:
                            merged_or_split = True
                            break
                if merged_or_split:
                    improved = True
                    continue
            break

    # ---------- validação completa de cronograma ----------
    def validate_full_schedule(self) -> bool:
        """
        Valida o cronograma completo de TODOS os veículos.

        Verifica se todas as viagens de todos os veículos respeitam:
        - Tmax por viagem
        - Janelas de tempo considerando tempo acumulado (Eq. 10)

        Returns:
            True se todos os cronogramas são válidos, False caso contrário
        """
        for k in range(self.inst.K):
            if not self.schedule_respects_time_windows_from(k, start_trip_idx=0):
                return False
        return True

    # ---------- utilidade ----------
    def copy(self) -> "Solution":
        from copy import deepcopy
        return deepcopy(self)
