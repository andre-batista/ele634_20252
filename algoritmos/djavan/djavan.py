# djavan.py
import random
import hashlib
import numpy as np
import pandas as pd
from collections import OrderedDict
from sortedcontainers import SortedList
from scipy.optimize import linprog
from copy import deepcopy
from itertools import combinations
from dados import Dados
from solucao import Solucao as SolucaoAndre

# ============================ [1] CONFIGURAÇÃO DE DADOS ============================
dados: Dados | None = None
conversao = None

def set_dados(d: Dados):
    global dados, conversao
    d_proc, conversao_local = reordenar_dados_por_janela(d)
    dados = d_proc
    conversao = conversao_local


# ============================ [2] REORDENAÇÃO DE DADOS ============================
def build_oracle(e):
    ordem_n = pd.Series(e).sort_values().index.to_numpy()
    ordem_np1 = np.concatenate(([0], ordem_n + 1))

    oracle = {}

    oracle['n'] = {}
    oracle['n']['ordem'] = ordem_n
    oracle['n']['forward'] = {orig: i for i, orig in enumerate(ordem_n)}
    oracle['n']['reverse'] = {i: orig for i, orig in enumerate(ordem_n)}

    oracle['n+1'] = {}
    oracle['n+1']['ordem'] = ordem_np1
    oracle['n+1']['forward'] = {orig: i for i, orig in enumerate(ordem_np1)}
    oracle['n+1']['reverse'] = {i: orig for i, orig in enumerate(ordem_np1)}

    return oracle

def apply_vector(x, ordem):
    return x[ordem]

def apply_matrix(M, ordem):
    return M[ordem][:, ordem]

def restore_vector(x_new, reverse_map):
    x_old = np.zeros_like(x_new)
    for new, orig in reverse_map.items():
        x_old[orig] = x_new[new]
    return x_old

def restore_matrix(M_new, reverse_map):
    n = len(M_new)
    M_old = np.zeros_like(M_new)
    for new_i, orig_i in reverse_map.items():
        for new_j, orig_j in reverse_map.items():
            M_old[orig_i, orig_j] = M_new[new_i, new_j]
    return M_old

def reorder_all(e, l, s, D, c, T):
    oracle = build_oracle(e)

    e_new = apply_vector(e, oracle['n']['ordem'])
    l_new = apply_vector(l, oracle['n']['ordem'])
    s_new = apply_vector(s, oracle['n+1']['ordem'])

    D_new = apply_matrix(D, oracle['n+1']['ordem'])
    c_new = apply_matrix(c, oracle['n+1']['ordem'])
    T_new = apply_matrix(T, oracle['n+1']['ordem'])

    return oracle, e_new, l_new, s_new, D_new, c_new, T_new

def reordenar_dados_por_janela(dados: Dados):
    n = dados.n
    K = dados.K
    r = dados.r
    T_max = dados.Tmax

    e = dados.e # n
    l = dados.l # n
    s = dados.s # n+1
    D = dados.D # (n+1, n+1)
    c = dados.c # (n+1, n+1)
    T = dados.T # (n+1, n+1)

    oracle, e_new, l_new, s_new, D_new, c_new, T_new = reorder_all(e, l, s, D, c, T)

    dados = Dados(
        numeroRequisicoes=n,
        numeroMaximoViagens=r,
        numeroOnibus=K,
        distanciaRequisicoes=D_new,
        custo=c_new,
        tempoServico=s_new,
        tempoRequisicoes=T_new,
        inicioJanela=e_new,
        fimJanela=l_new,
        tempoMaximo=T_max,
    )

    return dados, oracle


# ============================ [3] ESTRUTURA DE DADOS ============================
class Lista(SortedList):
    def max(self):
        """Retorna o maior elemento da lista (ou None se estiver vazia)."""
        if not self:
            return None
        return self[-1]

    def min(self):
        """Retorna o menor elemento da lista (ou None se estiver vazia)."""
        if not self:
            return None
        return self[0]

class SForest:
    def __init__(self, X=None):
        self.__dict__.update(dados.__dict__)
        
        if X is None:
            self.X = [[Lista() for _ in range(self.r)] for _ in range(self.K)]
        else:
            self.X = X

        self.I = [[[-1, -1] for _ in range(self.r)] for _ in range(self.K)]
        self.It = [[[-1, -1] for _ in range(self.r)] for _ in range(self.K)]
        self.M = {i: Lista() for i in range(1, self.n+1)}
        self.Mt = {i: Lista() for i in range(1, self.n+1)}
        self.H = {}
        
        for k in range(self.K):
            routes = self.X[k]
            for v in range(self.r):
                route = routes[v]
                for value in route:
                    self.H[value] = (k, v)

                lb, ub = 1, self.n
                if v != 0:
                    lb = routes[v-1].max()
                if v != self.r-1:
                    if len(routes[v+1]) > 0:
                        ub = routes[v+1].min()

                if len(route) <= 1 and len(routes[v-1]) == 1:
                    lb += 1
                    
                self.I[k][v] = [lb, ub]
                for p in range(lb, ub + 1):
                    if p in route:
                        continue
                    self.M[p].add((k, v))

                if len(route) != 0:
                    if v != 0:
                        ubt = self.I[k][v-1][1]
                    else:
                        ubt = route.min()
                else:
                    ubt = -1

                self.It[k][v] = [lb, ubt]
                if len(routes[-1]) == 0:
                    for p in range(lb, ubt + 1):
                        if p in route:
                            continue
                        self.Mt[p].add((k, v))

                if len(route) == 0:
                    break

        for k in range(self.K):
            for v in range(self.r):
                if len(self.X[k][v]) == 0:
                    break

                if len(self.X[k][v]) == 1:
                    i = self.X[k][v][0]
                    kh, vh = self.H[i]
                    self.Mt[i] = [(kk, vv) for (kk, vv) in self.Mt[i] if kk != kh]

    def get(self, k, v):
        return self.X[k][v]
    
    def add(self, k, v, value):
        self.X[k][v].add(value)
        self.H[value] = (k, v)

    def remove(self, value):
        k, v = self.H[value]

        self.X[k][v].remove(value)
        self.H.pop(value)

        return k, v
        
    def move(self, k, v, value, insert=False):
        kr, vr = self.remove(value)

        if insert:
            self.X[k].insert(v, Lista())
            self.X[k].pop(-1)

        self.add(k, v, value)

        if len(self.X[kr][vr]) == 0:
            self.X[kr].append(Lista())
            self.X[kr].pop(vr)

            if kr == k and vr < v:
                home = self.H[value]
                self.H[value] = (home[0], home[1]-1)

            return True, kr, vr
        
        return False, kr, vr

    def swap(self, value1, value2):
        k1, v1 = self.H[value1]
        k2, v2 = self.H[value2]

        self.X[k1][v1].remove(value1)
        self.X[k2][v2].remove(value2)

        self.X[k1][v1].add(value2)
        self.X[k2][v2].add(value1)

        self.H[value1] = (k2, v2)
        self.H[value2] = (k1, v1)

    def __repr__(self):
        def format_matrix(matrix):
            str_matrix = [[str(cell) for cell in row] for row in matrix]
            col_widths = [max(len(str_matrix[k][r]) for k in range(self.K)) for r in range(self.r)]
            lines = []
            for k in range(self.K):
                row = "  ".join(str_matrix[k][r].ljust(col_widths[r]) for r in range(self.r))
                lines.append(f"  {row}")
            return "\n".join(lines)

        lines = []
        lines.append("X (rotas):")
        lines.append(format_matrix([[list(self.X[k][r]) for r in range(self.r)] for k in range(self.K)]))

        return "\n".join(lines)


# ============================ [4] VIAGEM ============================
class CacheLP:
    def __init__(self, max_size=2048, decimals=8):
        self.max_size = int(max_size)
        self.decimals = int(decimals)
        self._data = OrderedDict()

    def _normaliza_array_float(self, x):
        x = np.asarray(x, dtype=float)
        mask = np.isfinite(x)
        x2 = x.copy()
        if np.any(mask):
            x2[mask] = np.round(x2[mask], self.decimals)
        return x2

    def cria_chave(self, tempos, janelas):
        cols = np.asarray(tempos.columns, dtype=int)

        s = self._normaliza_array_float(tempos.loc["s"].to_numpy())
        T = self._normaliza_array_float(tempos.loc["T"].to_numpy())
        e = self._normaliza_array_float(janelas.loc["e"].to_numpy())
        l = self._normaliza_array_float(janelas.loc["l"].to_numpy())

        payload = b"".join([
            cols.tobytes(),
            s.tobytes(),
            T.tobytes(),
            e.tobytes(),
            l.tobytes(),
        ])

        return hashlib.sha256(payload).hexdigest()

    def get(self, key):
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.max_size:
            self._data.popitem(last=False)

# random.seed(1)
_CACHE_LP = CacheLP(max_size=1e6, decimals=8)

def cria_matriz_onibus(rotas_onibus, dados):

    col_labels = []
    A_list, B_list = [], []
    s_list, T_list = [], []
    e_list, l_list = [], []

    for rota_obj in rotas_onibus:
        rota = list(rota_obj)
        if len(rota) == 0:
            break

        rota_ext = [0] + rota + [0]

        for idx in range(len(rota_ext) - 1):
            i = rota_ext[idx]
            j = rota_ext[idx + 1]

            col_labels.append(i)
            A_list.append(np.nan)
            B_list.append(np.nan)

            s_list.append(dados.s[i])
            T_list.append(dados.T[i, j])

            if j != 0:
                e_list.append(dados.e[j - 1])
                l_list.append(dados.l[j - 1])
            else:
                e_list.append(None)
                l_list.append(None)

    if len(col_labels) == 0:
        tempos = pd.DataFrame()
        janelas = pd.DataFrame()
        return tempos, janelas

    tempos = pd.DataFrame(
        {"A": A_list, "B": B_list, "s": s_list, "T": T_list},
        index=col_labels,
    ).T

    janelas = pd.DataFrame(
        {"e": e_list, "l": l_list},
        index=col_labels,
    ).T

    return tempos, janelas

def calcular_espera_mais_cedo(tempos, janelas, A0=0.0):

    cols = list(tempos.columns)
    n = len(cols)
    if n == 0:
        return tempos, 0.0

    s = tempos.loc["s"].to_numpy(dtype=float)
    T = tempos.loc["T"].to_numpy(dtype=float)
    e = janelas.loc["e"].to_numpy(dtype=float)
    l = janelas.loc["l"].to_numpy(dtype=float)

    A = np.zeros(n)
    B = np.zeros(n)
    folgas = []

    for j in range(n):
        if j == 0:
            A[j] = A0
        else:
            A[j] = A[j - 1] + B[j - 1] + s[j - 1] + T[j - 1]

        if j == n - 1:
            B[j] = 0.0
            continue

        if np.isnan(e[j]) or np.isnan(l[j]):
            B[j] = 0.0
            continue

        AsT = A[j] + s[j] + T[j]
        e_j = e[j]
        l_j = l[j]

        if AsT < e_j:
            B[j] = e_j - AsT
            folgas.append(l_j - e_j)
        else:
            B[j] = 0.0
            folgas.append(l_j - AsT)

    tempos.loc["A"] = A
    tempos.loc["B"] = B

    penalizacao_janelas = sum(1 for f in folgas if f < 0)

    return tempos, penalizacao_janelas

def calcula_tempos_viagens(tempos, dados):
    cols = list(tempos.columns)
    n = len(cols)
    if n == 0:
        return [], 0.0

    s = tempos.loc["s"].to_numpy(dtype=float)
    T = tempos.loc["T"].to_numpy(dtype=float)
    A = tempos.loc["A"].to_numpy(dtype=float)
    B = tempos.loc["B"].to_numpy(dtype=float)

    labels = np.array(cols)
    start_indices = [idx for idx, lab in enumerate(labels) if lab == 0]
    if not start_indices:
        return [], 0.0

    trip_bounds = []
    for t, s_idx in enumerate(start_indices):
        if t < len(start_indices) - 1:
            e_idx = start_indices[t + 1] - 1
        else:
            e_idx = n - 1
        trip_bounds.append((s_idx, e_idx))

    T_viagens = []
    penalizacao_viagens = 0.0

    for s_idx, e_idx in trip_bounds:
        col_last_sum = A[e_idx] + B[e_idx] + s[e_idx] + T[e_idx]
        T_viagem = col_last_sum - A[s_idx]
        T_viagens.append(float(T_viagem))
        if T_viagem > dados.Tmax:
            penalizacao_viagens += 1

    return T_viagens, penalizacao_viagens

def otimizar_onibus_minmax(tempos, janelas):
    cols = list(tempos.columns)
    n = len(cols)
    if n == 0:
        return tempos.copy()

    s = tempos.loc["s"].to_numpy(dtype=float)
    T = tempos.loc["T"].to_numpy(dtype=float)
    e = janelas.loc["e"].to_numpy(dtype=float)
    l = janelas.loc["l"].to_numpy(dtype=float)

    labels = np.array(cols)
    start_indices = [idx for idx, lab in enumerate(labels) if lab == 0]
    if not start_indices:
        return tempos.copy()

    trip_bounds = []
    for t, s_idx in enumerate(start_indices):
        if t < len(start_indices) - 1:
            e_idx = start_indices[t + 1] - 1
        else:
            e_idx = n - 1
        trip_bounds.append((s_idx, e_idx))

    m = 2 * n + 1
    c = np.zeros(m, dtype=float)
    c[-1] = 1.0

    A_eq_rows = []
    b_eq = []

    row = np.zeros(m, dtype=float)
    row[0] = 1.0
    A_eq_rows.append(row)
    b_eq.append(0.0)

    for j in range(n - 1):
        row = np.zeros(m, dtype=float)
        row[j + 1] = 1.0
        row[j] -= 1.0
        row[n + j] -= 1.0
        A_eq_rows.append(row)
        b_eq.append(s[j] + T[j])

    A_eq = np.vstack(A_eq_rows)
    b_eq = np.array(b_eq, dtype=float)

    A_ub_rows = []
    b_ub = []

    for j in range(n - 1):
        if not np.isnan(e[j]):
            row = np.zeros(m, dtype=float)
            row[j + 1] = -1.0
            A_ub_rows.append(row)
            b_ub.append(-e[j])
        if not np.isnan(l[j]):
            row = np.zeros(m, dtype=float)
            row[j + 1] = 1.0
            A_ub_rows.append(row)
            b_ub.append(l[j])

    for (s_idx, e_idx) in trip_bounds:
        row = np.zeros(m, dtype=float)
        row[e_idx] = 1.0
        row[n + e_idx] = 1.0
        row[s_idx] -= 1.0
        row[-1] -= 1.0
        A_ub_rows.append(row)
        b_ub.append(-(s[e_idx] + T[e_idx]))

    if A_ub_rows:
        A_ub = np.vstack(A_ub_rows)
        b_ub = np.array(b_ub, dtype=float)
    else:
        A_ub = None
        b_ub = None

    bounds = []
    for _ in range(n):
        bounds.append((None, None))
    for _ in range(n):
        bounds.append((0.0, None))
    bounds.append((0.0, None))

    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not res.success:
        raise ValueError(f"Erro na otimização linprog, status: {res.status}, message: {res.message}")

    x = res.x
    A_sol = x[0:n]
    B_sol = x[n:2 * n]

    tempos_opt = tempos.copy()
    tempos_opt.loc["A"] = A_sol
    tempos_opt.loc["B"] = B_sol

    return tempos_opt

def otimizar_onibus_minmax_com_cache(tempos, janelas, cache_lp=_CACHE_LP):
    cols = list(tempos.columns)
    n = len(cols)
    if n == 0:
        return tempos.copy()

    key = cache_lp.cria_chave(tempos, janelas)

    hit = cache_lp.get(key)
    if hit is not None:
        A_sol, B_sol = hit
        tempos_opt = tempos.copy()
        tempos_opt.loc["A"] = A_sol
        tempos_opt.loc["B"] = B_sol
        return tempos_opt

    tempos_opt = otimizar_onibus_minmax(tempos, janelas)

    A_sol = tempos_opt.loc["A"].to_numpy(dtype=float).copy()
    B_sol = tempos_opt.loc["B"].to_numpy(dtype=float).copy()
    cache_lp.set(key, (A_sol, B_sol))

    return tempos_opt

def analisa_onibus(rotas_onibus, dados):
    tempos, janelas = cria_matriz_onibus(rotas_onibus, dados)
    tempos, penalizacao_janela = calcular_espera_mais_cedo(tempos, janelas, A0=0)
    if penalizacao_janela == 0:
        tempos = otimizar_onibus_minmax_com_cache(tempos, janelas)
    Tviagens, penalizacao_viagens = calcula_tempos_viagens(tempos, dados)

    return tempos, Tviagens, penalizacao_janela, penalizacao_viagens


# ============================ [5] SOLUÇÃO ============================
def _is_better(
    fx,
    best_fx,
    score=None,
    best_score=None,
    eps=1e-6,
    score_eps=1e-9,
):
    if fx < best_fx - eps:
        return True
    if fx > best_fx + eps:
        return False

    if score is not None and best_score is not None:
        if score > best_score + score_eps:
            return True

    return False


class Solucao:
    contador_objetivo = 0
    cache_eval = {}

    def __init__(self, x0=None):
        self.__dict__.update(dados.__dict__)

        self.kmax = 3
        self.fx = None
        self.total_travel_time = None

        if x0 is None:
            X_init = None
        elif isinstance(x0, Solucao):
            X_init = x0.forest.X
        elif isinstance(x0, SForest):
            X_init = x0.X
        else:
            X_init = x0

        self.forest = SForest(X=X_init)

        self.coeficiente_penalizacao = 1e6
        self.coeficiente_eps = 1e-4
        
    
    def _hash_state(self, X):
        serialized = str([[list(sl) for sl in row] for row in X])
        return hashlib.sha1(serialized.encode()).hexdigest()

    def eval(self):
        state_hash = self._hash_state(self.forest.X)

        if state_hash in Solucao.cache_eval:
            cached_fx, cached_tt = Solucao.cache_eval[state_hash]
            self.fx = cached_fx
            self.total_travel_time = cached_tt
            return self.fx

        if Solucao.contador_objetivo >= Solucao.budget:
            if self.fx is None:
                self.fx = np.inf
                self.total_travel_time = None
            return self.fx

        Solucao.contador_objetivo += 1

        custo_total = 0.0
        penalizacao_total = 0.0
        total_travel_time = 0.0

        for rotas_onibus in self.forest.X:
            tempos, Tviagens, penalizacao_janela, penalizacao_viagens = analisa_onibus(rotas_onibus, self)

            requisicoes_onibus = list(tempos.columns) + [0]
            for i, j in zip(requisicoes_onibus[:-1], requisicoes_onibus[1:]):
                custo_total += self.c[i][j]

            penalizacao_total += penalizacao_janela + penalizacao_viagens
            total_travel_time += float(sum(Tviagens))

        penalizacao_total = penalizacao_total * self.coeficiente_penalizacao
        self.fx = float(custo_total + penalizacao_total)
        self.total_travel_time = float(total_travel_time)


        Solucao.cache_eval[state_hash] = (self.fx, self.total_travel_time)

        return self.fx

    def gerar_solucao_gulosa(self):
        base = Solucao()
        K = base.K
        r = base.r
        n = base.n

        X = [[Lista() for _ in range(r)] for _ in range(K)]
        usados = set()

        current = Solucao(X)
        current.eval()

        for value in range(1, n + 1):
            if value in usados:
                continue

            X_cur = current.forest.X

            best_fx = np.inf
            best_X = None

            M = current.forest.M.get(value, [])
            Mt = current.forest.Mt.get(value, [])

            for (k, v) in M:
                X_new = deepcopy(X_cur)
                s_new = Solucao(X_new)
                s_new.forest.add(k, v, value)
                fx = s_new.eval()

                if fx < best_fx:
                    best_fx = fx
                    best_X = s_new.forest.X

            for (k, v) in Mt:
                X_new = deepcopy(X_cur)
                s_new = Solucao(X_new)

                s_new.forest.X[k].insert(v, Lista())
                s_new.forest.X[k].pop(-1)
                s_new.forest.add(k, v, value)

                fx = s_new.eval()

                if fx < best_fx:
                    best_fx = fx
                    best_X = s_new.forest.X

            current = Solucao(best_X)
            current.eval()
            usados.add(value)

        return current

    def shake(self, N, debug=False):
        current = self
        for _ in range(int(1.5*N)):
            nxt = current.stochastic_neighbor(N=N)
            current = nxt

        current.eval()
        return current

    def best_improvement(self, N=1):
        if N == 1:
            best_fx = self.eval()
            best_score = -self.total_travel_time if self.total_travel_time is not None else None
            best_move = None

            for value, lista in self.forest.M.items():
                for k, v in lista:
                    empty, kr, vr = self.forest.move(k, v, value)

                    fx = self.eval()
                    score = -self.total_travel_time if self.total_travel_time is not None else None

                    if _is_better(fx, best_fx, score=score, best_score=best_score):
                        best_fx = fx
                        best_score = score
                        best_move = (k, v, value)

                    self.forest.move(kr, vr, value, insert=empty)

            if best_move is None:
                self.eval()
                return self

            k_best, v_best, value_best = best_move
            empty, kr, vr = self.forest.move(k_best, v_best, value_best)
            x = Solucao(deepcopy(self.forest))
            self.forest.move(kr, vr, value_best, insert=empty)

        elif N == 2:
            Mt = self.forest.Mt

            best_fx = self.eval()
            best_score = -self.total_travel_time if self.total_travel_time is not None else None
            best_move = None

            for value, lista in Mt.items():
                for k, v in lista:
                    self.forest.X[k].insert(v, Lista())
                    self.forest.X[k].pop(-1)

                    empty, kr, vr = self.forest.move(k, v, value)

                    fx = self.eval()
                    score = -self.total_travel_time if self.total_travel_time is not None else None

                    if _is_better(fx, best_fx, score=score, best_score=best_score):
                        best_fx = fx
                        best_score = score
                        best_move = (k, v, value)

                    self.forest.move(kr, vr, value, insert=empty)

            if best_move is None:
                self.eval()
                return self

            k_best, v_best, value_best = best_move
            self.forest.X[k_best].insert(v_best, Lista())
            self.forest.X[k_best].pop(-1)
            empty, kr, vr = self.forest.move(k_best, v_best, value_best)
            x = Solucao(deepcopy(self.forest))
            self.forest.move(kr, vr, value_best, insert=empty)

        elif N == 3:
            H = self.forest.H
            M = self.forest.M

            best_fx = self.eval()
            best_score = -self.total_travel_time if self.total_travel_time is not None else None
            best_swap = None

            for i, j in combinations(range(1, self.n + 1), 2):
                if H[i] in M[j] and H[j] in M[i] and H[i][0] != H[j][0]:
                    self.forest.swap(i, j)
                    fx = self.eval()
                    score = -self.total_travel_time if self.total_travel_time is not None else None

                    if _is_better(fx, best_fx, score=score, best_score=best_score):
                        best_fx = fx
                        best_score = score
                        best_swap = (i, j)

                    self.forest.swap(i, j)

            if best_swap is None:
                self.eval()
                return self

            i_best, j_best = best_swap
            self.forest.swap(i_best, j_best)
            x = Solucao(deepcopy(self.forest))
            self.forest.swap(i_best, j_best)

        else:
            raise NotImplementedError("best_improvement só suporta N=1,2,3")
            
        x.eval()
        return x
    
    def stochastic_neighbor(self, N=1):
        if N == 1:
            all_moves = []
            for value, lista in self.forest.M.items():
                for (k, v) in lista:
                    all_moves.append((value, k, v))

            if not all_moves:
                return self

            value, k, v = random.choice(all_moves)

            empty, kr, vr = self.forest.move(k, v, value)

            x = Solucao(deepcopy(self.forest))

            self.forest.move(kr, vr, value, insert=empty)

        elif N == 2:
            Mt = self.forest.Mt

            all_moves = []
            for value, lista in Mt.items():
                for (k, v) in lista:
                    all_moves.append((value, k, v))

            if not all_moves:
                return self

            value, k, v = random.choice(all_moves)

            self.forest.X[k].insert(v, Lista())
            self.forest.X[k].pop(-1)

            empty, kr, vr = self.forest.move(k, v, value)

            x = Solucao(deepcopy(self.forest))

            self.forest.move(kr, vr, value, insert=empty)
        elif N == 3:
            H = self.forest.H
            M = self.forest.M

            feasible_swaps = []
            for i, j in combinations(range(1, self.n + 1), 2):
                if H[i] in M[j] and H[j] in M[i] and H[i][0] != H[j][0]:
                    feasible_swaps.append((i, j))

            if not feasible_swaps:
                return self

            i, j = random.choice(feasible_swaps)

            self.forest.swap(i, j)
            x = Solucao(deepcopy(self.forest))
            self.forest.swap(i, j)

        else:
            raise NotImplementedError("stochastic_neighbor só suporta N=1,2,3")

        x.eval()
        return x

    def __repr__(self):
        txt = self.forest.__repr__()
        txt += f"\nCusto total (fx): {self.fx}\n"
        txt += f"Contador de avaliações de função objetivo: {Solucao.contador_objetivo}\n"
        txt += f"Budget total utilizado: {100 * Solucao.contador_objetivo / (10 * self.n * self.K * self.r):.2f}%\n"
        return txt


# ============================ [6] VNS ============================
class SolverBase:
    def __init__(self):
        self.fx = []
        self.eps = 1e-6
        self.stats = {
            1: {"calls": 0, "improvements": 0, "delta_fx": []},
            2: {"calls": 0, "improvements": 0, "delta_fx": []},
            3: {"calls": 0, "improvements": 0, "delta_fx": []}
        }

    def neighborhood_change(self, candidate, x, k):
        best_fx = x.fx
        fx = candidate.fx

        best_score = -x.total_travel_time if getattr(x, "total_travel_time", None) is not None else None
        score = -candidate.total_travel_time if getattr(candidate, "total_travel_time", None) is not None else None

        self.stats[k]["calls"] += 1

        if _is_better(fx, best_fx, score=score, best_score=best_score):
            self.fx.append(fx)
            self.stats[k]["improvements"] += 1
            self.stats[k]["delta_fx"].append(best_fx - fx)
            return candidate, 1
        else:
            return x, k + 1

class VND(SolverBase):
    def __init__(self):
        super().__init__()

    def solve(self, x0):
        x = Solucao(x0)
        x.eval()

        self.fx = [x.fx]

        k = 1
        while k <= x.kmax:
            candidate = x.best_improvement(k)
            x, k = self.neighborhood_change(candidate, x, k)

        return x

class GVNS(SolverBase):
    def __init__(self):
        super().__init__()
        self.vnd = VND()

    def solve(self, x0):
        x = Solucao(x0)
        x.eval()

        self.fx = [x.fx]

        k = 1
        while k <= x.kmax:
            shake = x.shake(k)
            cand = self.vnd.solve(shake)
            x, k = self.neighborhood_change(cand, x, k)

        return x


# ============================ [7] EXTRAIR ROTA E TEMPOS DE CHEGADA ============================
def extrair_resultados(x, usar_oraculo=True):
    rota = {}
    chegada = {}
    fx = x.fx

    X = x.forest.X
    for k in range(1, x.K+1):
        rota[k] = {}
        chegada[k] = {}

        for v in range(1, x.r+1):
            data = X[k-1][v-1]

            chegada[k][v] = []
            if len(data) == 0:
                rota[k][v] = []
            else:
                rota[k][v] = [0] + list(data) + [0]

    for k, rotas_onibus in enumerate(X, start=1):
        tempos, _, _, _ = analisa_onibus(rotas_onibus, x)

        v = 0
        for j, req in enumerate(tempos):
            if req == 0:
                v += 1
                chegada[k][v] = [round(abs(float(tempos.iloc[0, j])), 5)]

            chegada[k][v].append(round(float(tempos.iloc[:, j].sum()), 5))

    if usar_oraculo and conversao is not None:
        reverse_map = conversao["n+1"]["reverse"]
        rota_original = {}

        for k, dict_viagens in rota.items():
            rota_original[k] = {}
            for v, caminho in dict_viagens.items():
                rota_original[k][v] = [
                    int(reverse_map[node]) for node in caminho
                ]

        rota = rota_original

    sol = SolucaoAndre()
    sol.rota = rota
    sol.chegada = chegada
    sol.fx = fx

    return sol


# ============================ [8] FUNÇÃO PRINCIPAL ============================
def resolva(dados: Dados, numero_avaliacoes: int) -> Solucao:
    set_dados(dados)
    Solucao.cache_eval.clear()
    Solucao.contador_objetivo = 0
    Solucao.budget = numero_avaliacoes

    x0 = Solucao()
    x0 = x0.gerar_solucao_gulosa()

    solver = GVNS()
    x = solver.solve(x0)
    sol = extrair_resultados(x)

    return sol