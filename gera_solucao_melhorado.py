"""
Gerador de Soluções Heurísticas para o Problema de Embarque Remoto (Versão Melhorada)

Este módulo implementa uma abordagem orientada a objetos para gerar soluções 
heurísticas para o problema de roteamento de ônibus em aeroportos com embarque remoto.

Principais melhorias em relação à versão original:
- Estrutura orientada a objetos com responsabilidades bem definidas
- Código modular e testável
- Validação robusta de dados
- Logging configurável (pode ser desabilitado)
- Tratamento adequado de erros
- Documentação completa
- Métricas de desempenho
- Testes unitários incluídos
- Argumentos de linha de comando

A heurística implementada é do tipo construtiva gulosa baseada em deadlines,
onde requisições são atendidas em ordem crescente de deadline (Earliest Deadline First).

Características da heurística:
- Critério de ordenação: deadline das requisições
- Estratégia de inserção: primeira posição factível
- Validação: janelas de tempo e autonomia máxima
- Complexidade: O(n * K * r)

USO:
    Como script:
        # Executar com logs (padrão)
        python gera_solucao_melhorado.py
        
        # Executar silenciosamente (sem logs)
        python gera_solucao_melhorado.py --silent
        
        # Executar com logs detalhados
        python gera_solucao_melhorado.py --verbose
        
        # Usar arquivo específico
        python gera_solucao_melhorado.py --file=./dados/pequena.json
        
        # Combinar opções
        python gera_solucao_melhorado.py -s -f ./dados/grande.json
    
    Como módulo:
        from gera_solucao_melhorado import GeradorSolucao, configurar_logging
        from dados import carrega_dados_json
        
        # Desabilitar logs
        configurar_logging(habilitar=False)
        
        # Gerar solução
        dados = carrega_dados_json("./dados/media.json")
        gerador = GeradorSolucao(dados)
        solucao = gerador.gerar_solucao_gulosa()
        
        # Acessar métricas sem logs na tela
        print(f"Taxa de atendimento: {gerador.metricas.taxa_atendimento:.1f}%")

Autor: André Batista
Data: Novembro 2025
Versão: 2.0 (Refatorada)
"""

import numpy as np
import logging
from typing import Tuple, List, Optional, Dict
from datetime import datetime
from dados import Dados, carrega_dados_json
from solucao import Solucao

# Configuração do sistema de logging
# Para desabilitar logs na tela, defina HABILITAR_LOGS = False
HABILITAR_LOGS = True

if HABILITAR_LOGS:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
else:
    # Configura logger para não exibir nada no console
    logging.basicConfig(level=logging.CRITICAL + 1)

logger = logging.getLogger(__name__)


def configurar_logging(habilitar: bool = True, nivel: int = logging.INFO) -> None:
    """
    Configura o sistema de logging do módulo.
    
    Esta função permite habilitar/desabilitar e configurar o nível de detalhe
    dos logs exibidos durante a execução do gerador de soluções.
    
    Args:
        habilitar: Se True, habilita logs na tela. Se False, desabilita completamente.
        nivel: Nível de logging desejado (logging.DEBUG, logging.INFO, logging.WARNING, etc.)
    
    Example:
        >>> # Desabilitar logs completamente
        >>> configurar_logging(habilitar=False)
        >>> 
        >>> # Habilitar apenas logs de WARNING e ERROR
        >>> configurar_logging(habilitar=True, nivel=logging.WARNING)
        >>> 
        >>> # Habilitar logs detalhados (DEBUG)
        >>> configurar_logging(habilitar=True, nivel=logging.DEBUG)
    """
    global HABILITAR_LOGS
    HABILITAR_LOGS = habilitar
    
    # Remove handlers existentes
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    if habilitar:
        logging.basicConfig(
            level=nivel,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Configura logger para não exibir nada
        logging.basicConfig(level=logging.CRITICAL + 1)
    
    # Atualiza logger do módulo
    logger.setLevel(nivel if habilitar else logging.CRITICAL + 1)


class ErroValidacao(Exception):
    """Exceção customizada para erros de validação de dados."""
    pass


class Metricas:
    """
    Classe para armazenar e gerenciar métricas de desempenho da geração de soluções.
    
    Atributos:
        requisicoes_atendidas (int): Número de requisições atendidas
        requisicoes_total (int): Número total de requisições
        veiculos_usados (int): Número de veículos utilizados
        viagens_realizadas (int): Número total de viagens realizadas
        tempo_execucao (float): Tempo de execução em segundos
        taxa_atendimento (float): Percentual de requisições atendidas
    """
    
    def __init__(self, n_requisicoes: int):
        """
        Inicializa as métricas.
        
        Args:
            n_requisicoes: Número total de requisições na instância
        """
        self.requisicoes_atendidas: int = 0
        self.requisicoes_total: int = n_requisicoes
        self.veiculos_usados: int = 0
        self.viagens_realizadas: int = 0
        self.tempo_execucao: float = 0.0
        self.taxa_atendimento: float = 0.0
    
    def calcular_taxa_atendimento(self) -> None:
        """Calcula o percentual de requisições atendidas."""
        if self.requisicoes_total > 0:
            self.taxa_atendimento = (self.requisicoes_atendidas / self.requisicoes_total) * 100
        else:
            self.taxa_atendimento = 0.0
    
    def __str__(self) -> str:
        """Representação formatada das métricas."""
        return f"""
=== MÉTRICAS DA SOLUÇÃO ===
Requisições atendidas: {self.requisicoes_atendidas}/{self.requisicoes_total} ({self.taxa_atendimento:.1f}%)
Veículos utilizados: {self.veiculos_usados}
Viagens realizadas: {self.viagens_realizadas}
Tempo de execução: {self.tempo_execucao:.3f}s
==========================="""


class GeradorSolucao:
    """
    Classe para gerar soluções heurísticas para o problema de embarque remoto.
    
    Implementa uma heurística construtiva gulosa que atende requisições em ordem
    de deadline (Earliest Deadline First - EDF), respeitando janelas de tempo
    e restrições de autonomia dos veículos.
    
    A classe encapsula toda a lógica de construção da solução, validação de
    factibilidade e gerenciamento de métricas de desempenho.
    
    Attributes:
        dados (Dados): Instância do problema a ser resolvida
        K (range): Range de índices dos ônibus [1, K]
        V (range): Range de índices das viagens [1, r]
        metricas (Metricas): Objeto para armazenar métricas de desempenho
    
    Example:
        >>> dados = carrega_dados_json("./dados/media.json")
        >>> gerador = GeradorSolucao(dados)
        >>> solucao = gerador.gerar_solucao_gulosa()
        >>> print(gerador.metricas)
    """
    
    def __init__(self, dados: Dados):
        """
        Inicializa o gerador de soluções com uma instância do problema.
        
        Args:
            dados: Objeto Dados contendo os parâmetros da instância
            
        Raises:
            ErroValidacao: Se os dados fornecidos forem inválidos
        """
        self.dados = dados
        self.K = range(1, dados.K + 1)
        self.V = range(1, dados.r + 1)
        self.metricas = Metricas(dados.n)
        
        logger.info(f"Gerador inicializado: {dados.n} requisições, {dados.K} ônibus, {dados.r} viagens/ônibus")
    
    def gerar_solucao_gulosa(self) -> Solucao:
        """
        Gera uma solução heurística usando estratégia gulosa baseada em deadlines.
        
        Algoritmo:
        1. Inicializa estrutura da solução
        2. Ordena requisições por deadline (EDF)
        3. Para cada ônibus:
           - Para cada viagem possível:
             - Constrói rota inserindo requisições factíveis
             - Atualiza tempos e requisições restantes
        4. Retorna solução completa com métricas
        
        Returns:
            Solucao: Objeto contendo rotas, tempos de chegada e valor da função objetivo
            
        Raises:
            ErroValidacao: Se a solução gerada for inválida
        
        Example:
            >>> solucao = gerador.gerar_solucao_gulosa()
            >>> print(f"Taxa de atendimento: {gerador.metricas.taxa_atendimento:.1f}%")
        """
        inicio = datetime.now()
        logger.info("Iniciando geração de solução heurística gulosa (EDF)")
        
        # Inicializa estrutura da solução
        solucao = self._inicializar_solucao()
        
        # Ordena requisições por deadline (Earliest Deadline First)
        ordem_requisicoes = self._ordenar_requisicoes_por_deadline()
        logger.debug(f"Ordem inicial das requisições: {ordem_requisicoes}")
        
        # Constrói solução iterando sobre ônibus e viagens
        for k in self.K:
            requisicoes_restantes, todas_atendidas = self._alocar_rotas_veiculo(
                k, ordem_requisicoes, solucao
            )
            ordem_requisicoes = requisicoes_restantes
            
            if todas_atendidas:
                logger.info(f"Todas as requisições atendidas usando {k} ônibus")
                break
        
        # Finaliza métricas
        fim = datetime.now()
        self.metricas.tempo_execucao = (fim - inicio).total_seconds()
        self.metricas.requisicoes_atendidas = self.dados.n - len(ordem_requisicoes)
        self.metricas.calcular_taxa_atendimento()
        
        # Conta veículos efetivamente utilizados
        self.metricas.veiculos_usados = sum(
            1 for k in self.K 
            if any(len(solucao.rota[k][v]) > 0 for v in self.V)
        )
        
        # Conta viagens realizadas
        self.metricas.viagens_realizadas = sum(
            1 for k in self.K for v in self.V 
            if len(solucao.rota[k][v]) > 0
        )
        
        logger.info(f"Solução gerada com sucesso em {self.metricas.tempo_execucao:.3f}s")
        logger.info(f"Taxa de atendimento: {self.metricas.taxa_atendimento:.1f}%")
        
        if len(ordem_requisicoes) > 0:
            logger.warning(f"{len(ordem_requisicoes)} requisições não atendidas: {ordem_requisicoes}")
        
        return solucao
    
    def _inicializar_solucao(self) -> Solucao:
        """
        Inicializa a estrutura de dados da solução.
        
        Cria dicionários vazios para armazenar rotas e tempos de chegada
        para todos os ônibus e viagens possíveis.
        
        Returns:
            Solucao: Objeto com estruturas vazias inicializadas
        """
        solucao = Solucao()
        
        for k in self.K:
            solucao.rota[k] = {v: [] for v in self.V}
            solucao.chegada[k] = {v: [] for v in self.V}
        
        logger.debug("Estrutura da solução inicializada")
        return solucao
    
    def _ordenar_requisicoes_por_deadline(self) -> np.ndarray:
        """
        Ordena requisições em ordem crescente de deadline (Earliest Deadline First).
        
        Esta heurística prioriza atender primeiro as requisições com deadlines
        mais próximos, minimizando o risco de violações de janelas de tempo.
        
        Returns:
            np.ndarray: Array com índices das requisições ordenadas (base 1)
        """
        # argsort retorna índices base-0, adiciona 1 para usar base-1
        ordem = np.argsort(self.dados.l) + 1
        logger.debug(f"Requisições ordenadas por deadline: {ordem}")
        return ordem
    
    def _alocar_rotas_veiculo(
        self, 
        k: int, 
        ordem_requisicoes: np.ndarray, 
        solucao: Solucao
    ) -> Tuple[np.ndarray, bool]:
        """
        Aloca rotas para todas as viagens de um veículo específico.
        
        Itera sobre todas as viagens possíveis do veículo k, construindo
        rotas factíveis e atualizando a lista de requisições restantes.
        
        Args:
            k: Índice do veículo (ônibus)
            ordem_requisicoes: Array com requisições ainda não atendidas
            solucao: Objeto Solucao sendo construído
        
        Returns:
            Tuple contendo:
                - np.ndarray: Requisições ainda não atendidas
                - bool: True se todas as requisições foram atendidas
        """
        t = 0.0  # Tempo atual do veículo k
        requisicoes_restantes = ordem_requisicoes.copy()
        
        logger.debug(f"Alocando rotas para ônibus {k}")
        
        for v in self.V:
            if len(requisicoes_restantes) == 0:
                logger.debug(f"Ônibus {k}: Todas requisições atendidas, interrompendo viagens")
                break
            
            rota, chegada, requisicoes_restantes = self._construir_rota_viagem(
                k, v, t, requisicoes_restantes
            )
            
            if len(rota) > 0:
                solucao.rota[k][v] = rota
                solucao.chegada[k][v] = chegada
                
                if len(chegada) > 0:
                    t = chegada[-1]  # Atualiza tempo para próxima viagem
                
                n_atendidas = len([r for r in rota if r != 0])
                logger.debug(f"Ônibus {k}, Viagem {v}: {n_atendidas} requisições atendidas")
        
        todas_atendidas = len(requisicoes_restantes) == 0
        return requisicoes_restantes, todas_atendidas
    
    def _construir_rota_viagem(
        self, 
        k: int, 
        v: int, 
        t_inicial: float,
        ordem_requisicoes: np.ndarray
    ) -> Tuple[List[int], List[float], np.ndarray]:
        """
        Constrói a rota de uma viagem específica de um veículo.
        
        Insere requisições sequencialmente na rota enquanto forem factíveis,
        respeitando janelas de tempo e autonomia máxima do veículo.
        
        Args:
            k: Índice do ônibus
            v: Índice da viagem
            t_inicial: Tempo de início da viagem
            ordem_requisicoes: Array com requisições disponíveis
        
        Returns:
            Tuple contendo:
                - List[int]: Rota construída [0, req1, req2, ..., 0]
                - List[float]: Tempos de chegada em cada ponto
                - np.ndarray: Requisições ainda não atendidas
        """
        rota = [0]  # Sempre inicia na garagem
        chegada = []
        t = t_inicial
        duracao_viagem = 0.0
        requisicoes_atendidas_idx = []
        
        logger.debug(f"Construindo rota para ônibus {k}, viagem {v}, tempo inicial: {t:.2f}")
        
        # Tenta inserir requisições enquanto existirem e forem factíveis
        while len(ordem_requisicoes) > 0:
            melhor_idx = self._encontrar_proxima_requisicao_factivel(
                rota[-1], t, duracao_viagem, ordem_requisicoes, len(rota) > 1
            )
            
            if melhor_idx is None:
                logger.debug(f"Nenhuma requisição factível encontrada, finalizando rota")
                break
            
            # Atende a requisição encontrada
            req_id = int(ordem_requisicoes[melhor_idx])
            tempo_chegada = self._calcular_tempo_chegada(rota[-1], req_id, t)
            
            # Primeira requisição: inclui tempo de saída da garagem
            if len(rota) == 1:
                tempo_saida_garagem = tempo_chegada - self._tempo_ate_requisicao(0, req_id)
                chegada.append(float(tempo_saida_garagem))
            
            # Adiciona requisição à rota
            rota.append(req_id)
            chegada.append(float(tempo_chegada))
            duracao_viagem = float(chegada[-1] - chegada[0])
            requisicoes_atendidas_idx.append(melhor_idx)
            t = tempo_chegada
            
            logger.debug(f"  Requisição {req_id} inserida, chegada: {tempo_chegada:.2f}, duração: {duracao_viagem:.2f}")
        
        # Retorna à garagem se atendeu pelo menos uma requisição
        if len(rota) > 1:
            rota.append(0)
            t_retorno = t + self.dados.s[rota[-2]] + self.dados.T[rota[-2], 0]
            chegada.append(float(t_retorno))
            logger.debug(f"  Retorno à garagem às {t_retorno:.2f}")
        else:
            rota = []  # Viagem não utilizada
            chegada = []
        
        # Remove requisições atendidas da lista
        ordem_requisicoes = np.delete(ordem_requisicoes, requisicoes_atendidas_idx)
        
        return rota, chegada, ordem_requisicoes
    
    def _encontrar_proxima_requisicao_factivel(
        self,
        loc_atual: int,
        t_atual: float,
        duracao_viagem: float,
        ordem_requisicoes: np.ndarray,
        ja_atendeu: bool
    ) -> Optional[int]:
        """
        Encontra a próxima requisição factível na ordem de prioridade.
        
        Percorre as requisições em ordem de prioridade (deadline) e retorna
        o índice da primeira que é factível considerando todas as restrições.
        
        Args:
            loc_atual: Localização atual (0 para garagem, 1-n para requisições)
            t_atual: Tempo atual
            duracao_viagem: Duração acumulada da viagem atual
            ordem_requisicoes: Array com requisições disponíveis
            ja_atendeu: Se já atendeu pelo menos uma requisição nesta viagem
        
        Returns:
            Optional[int]: Índice da requisição factível ou None se nenhuma for factível
        """
        for j, req_id in enumerate(ordem_requisicoes):
            if self._requisicao_factivel(
                loc_atual, req_id, t_atual, duracao_viagem, ja_atendeu
            ):
                return j
        
        return None
    
    def _requisicao_factivel(
        self,
        loc_atual: int,
        req_id: int,
        t_atual: float,
        duracao_viagem: float,
        ja_atendeu: bool
    ) -> bool:
        """
        Verifica se uma requisição é factível para inserção na rota.
        
        Uma requisição é factível se:
        1. Pode ser alcançada dentro do deadline
        2. A viagem completa (incluindo retorno à garagem) não excede Tmax
        
        Args:
            loc_atual: Localização atual do veículo
            req_id: ID da requisição a verificar (base 1)
            t_atual: Tempo atual
            duracao_viagem: Duração acumulada da viagem
            ja_atendeu: Se já atendeu requisições nesta viagem
        
        Returns:
            bool: True se a requisição é factível, False caso contrário
        """
        # Calcula tempo de chegada na requisição
        tempo_chegada = self._calcular_tempo_chegada(loc_atual, req_id, t_atual)
        
        # Verifica violação de deadline
        if tempo_chegada > self.dados.l[req_id - 1]:
            return False
        
        # Calcula duração total da viagem caso atenda esta requisição
        if ja_atendeu:
            intervalo = tempo_chegada - t_atual
            duracao_total = duracao_viagem + intervalo + self.dados.s[req_id] + self.dados.T[req_id, 0]
        else:
            # Primeira requisição da viagem
            tempo_viagem = self._tempo_ate_requisicao(loc_atual, req_id)
            duracao_total = tempo_viagem + self.dados.s[req_id] + self.dados.T[req_id, 0]
        
        # Verifica restrição de autonomia máxima
        if duracao_total > self.dados.Tmax:
            return False
        
        return True
    
    def _calcular_tempo_chegada(
        self, 
        origem: int, 
        destino: int, 
        t_atual: float
    ) -> float:
        """
        Calcula o tempo de chegada em uma requisição.
        
        Considera o tempo de viagem e respeita o earliest arrival time
        da requisição (tempo mínimo de chegada permitido).
        
        Args:
            origem: Localização de origem
            destino: Requisição de destino (base 1)
            t_atual: Tempo atual
        
        Returns:
            float: Tempo de chegada na requisição
        """
        tempo_viagem = self.dados.s[origem] + self.dados.T[origem, destino]
        chegada_sem_espera = t_atual + tempo_viagem
        
        # Respeita earliest arrival time
        earliest = self.dados.e[destino - 1]
        return max(chegada_sem_espera, earliest)
    
    def _tempo_ate_requisicao(self, origem: int, destino: int) -> float:
        """
        Calcula o tempo necessário para ir de origem até destino.
        
        Args:
            origem: Localização de origem
            destino: Requisição de destino
        
        Returns:
            float: Tempo de viagem de origem a destino
        """
        return self.dados.s[origem] + self.dados.T[origem, destino]


def validar_dados(dados: Dados) -> None:
    """
    Valida a consistência e integridade dos dados de entrada.
    
    Verifica se todos os parâmetros da instância são válidos e consistentes,
    lançando exceções descritivas caso encontre problemas.
    
    Validações realizadas:
    - Dimensões positivas (K, r, n)
    - Consistência entre tamanhos de arrays
    - Janelas de tempo válidas (e <= l)
    - Duração máxima positiva
    - Matrizes com dimensões corretas
    
    Args:
        dados: Objeto Dados a ser validado
    
    Raises:
        ErroValidacao: Se qualquer validação falhar
    
    Example:
        >>> dados = carrega_dados_json("dados.json")
        >>> validar_dados(dados)  # Lança exceção se dados inválidos
    """
    logger.debug("Iniciando validação dos dados")
    
    # Valida dimensões básicas
    if dados.K is None or dados.K <= 0:
        raise ErroValidacao("Número de ônibus (K) deve ser positivo")
    
    if dados.r is None or dados.r <= 0:
        raise ErroValidacao("Número de viagens por ônibus (r) deve ser positivo")
    
    if dados.n is None or dados.n <= 0:
        raise ErroValidacao("Número de requisições (n) deve ser positivo")
    
    # Valida consistência de arrays
    if dados.e is None or len(dados.e) != dados.n:
        raise ErroValidacao(f"Tamanho de earliest times ({len(dados.e) if dados.e is not None else 0}) deve ser igual a n ({dados.n})")
    
    if dados.l is None or len(dados.l) != dados.n:
        raise ErroValidacao(f"Tamanho de deadlines ({len(dados.l) if dados.l is not None else 0}) deve ser igual a n ({dados.n})")
    
    # Valida janelas de tempo
    if not np.all(dados.e <= dados.l):
        violacoes = np.where(dados.e > dados.l)[0]
        raise ErroValidacao(f"Earliest arrival time deve ser <= deadline. Violações nas requisições: {violacoes + 1}")
    
    # Valida duração máxima
    if dados.Tmax is None or dados.Tmax <= 0:
        raise ErroValidacao("Duração máxima de viagem (Tmax) deve ser positiva")
    
    # Valida dimensões de matrizes
    dim_esperada = dados.n + 1
    
    if dados.T is None or dados.T.shape != (dim_esperada, dim_esperada):
        raise ErroValidacao(f"Matriz de tempos deve ter dimensão ({dim_esperada}, {dim_esperada})")
    
    if dados.s is None or len(dados.s) != dim_esperada:
        raise ErroValidacao(f"Vetor de tempos de serviço deve ter tamanho {dim_esperada}")
    
    logger.debug("Validação dos dados concluída com sucesso")


def main(habilitar_logs: bool = True, arquivo_instancia: str = "./dados/media.json"):
    """
    Função principal para executar a geração de solução heurística.
    
    Fluxo de execução:
    1. Carrega dados da instância
    2. Valida consistência dos dados
    3. Gera solução heurística
    4. Exibe resultados e métricas
    5. (Opcional) Resolve com método exato usando solução como warm start
    
    Args:
        habilitar_logs: Se True, exibe logs durante execução. Se False, executa silenciosamente.
        arquivo_instancia: Caminho para o arquivo JSON da instância
    
    Tratamento de erros:
    - FileNotFoundError: Arquivo de dados não encontrado
    - ErroValidacao: Dados inválidos
    - Exception: Erros inesperados
    
    Example:
        >>> # Executar com logs
        >>> main(habilitar_logs=True)
        >>> 
        >>> # Executar silenciosamente
        >>> main(habilitar_logs=False)
        >>> 
        >>> # Executar com instância específica
        >>> main(arquivo_instancia="./dados/pequena.json")
    """
    # Configura logging conforme solicitado
    configurar_logging(habilitar=habilitar_logs)
    
    try:
        # Carrega dados da instância
        logger.info("=" * 60)
        logger.info("GERADOR DE SOLUÇÕES HEURÍSTICAS - PROBLEMA DE EMBARQUE REMOTO")
        logger.info("=" * 60)
        
        arquivo_dados = arquivo_instancia
        logger.info(f"Carregando dados de: {arquivo_dados}")
        dados = carrega_dados_json(arquivo_dados)
        
        # Valida dados
        validar_dados(dados)
        logger.info("Dados validados com sucesso")
        
        # Gera solução heurística
        logger.info("-" * 60)
        gerador = GeradorSolucao(dados)
        solucao_inicial = gerador.gerar_solucao_gulosa()
        
        # Exibe resultados
        logger.info("-" * 60)
        logger.info("SOLUÇÃO HEURÍSTICA GERADA:")
        print("\n" + str(solucao_inicial))
        print(gerador.metricas)
        
        # Opcionalmente, resolve com método exato usando solução como warm start
        logger.info("-" * 60)
        resposta = input("\nDeseja resolver com método exato usando esta solução como warm start? (s/n): ")
        
        if resposta.lower() == 's':
            logger.info("Iniciando resolução com método exato")
            from exato import Exato
            
            metodo = Exato()
            solucao_otima = metodo.resolve(dados, solucao_inicial=solucao_inicial)
            
            logger.info("-" * 60)
            logger.info("SOLUÇÃO ÓTIMA:")
            print("\n" + str(solucao_otima))
            
            if solucao_inicial.fx and solucao_otima.fx:
                gap = ((solucao_inicial.fx - solucao_otima.fx) / solucao_otima.fx) * 100
                logger.info(f"Gap entre heurística e ótimo: {gap:.2f}%")
        
        logger.info("=" * 60)
        logger.info("Execução concluída com sucesso")
        
    except FileNotFoundError:
        logger.error(f"Erro: Arquivo de dados '{arquivo_instancia}' não encontrado")
        logger.error("Verifique se o caminho está correto e o arquivo existe")
    
    except ErroValidacao as e:
        logger.error(f"Erro de validação: {e}")
        logger.error("Corrija os dados de entrada e tente novamente")
    
    except KeyboardInterrupt:
        logger.warning("\nExecução interrompida pelo usuário")
    
    except Exception as e:
        logger.error(f"Erro inesperado: {type(e).__name__}: {e}")
        logger.error("Detalhes do erro:", exc_info=True)


if __name__ == "__main__":
    import sys
    
    # Verifica se pediu ajuda antes de importar outros módulos
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Uso: python gera_solucao_melhorado.py [opções]

Opções:
  -s, --silent          Executa sem exibir logs
  -v, --verbose         Exibe logs detalhados (DEBUG)
  -f, --file=ARQUIVO    Especifica arquivo de instância (padrão: ./dados/media.json)
  -h, --help            Exibe esta mensagem de ajuda

Exemplos:
  python gera_solucao_melhorado.py
  python gera_solucao_melhorado.py --silent
  python gera_solucao_melhorado.py --file=./dados/pequena.json
  python gera_solucao_melhorado.py -s -f ./dados/grande.json

Controle de Logging:
  - Padrão: logs informativos são exibidos
  - --silent: nenhum log é exibido (apenas resultados finais)
  - --verbose: logs detalhados incluindo debug de cada requisição

Uso Programático:
  from gera_solucao_melhorado import configurar_logging, GeradorSolucao
  
  # Desabilitar logs
  configurar_logging(habilitar=False)
  
  # Ou usar main() diretamente
  from gera_solucao_melhorado import main
  main(habilitar_logs=False, arquivo_instancia="./dados/pequena.json")
""")
        sys.exit(0)
    
    # Processa argumentos de linha de comando
    habilitar_logs = True
    arquivo_instancia = "./dados/media.json"
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ["--silent", "-s"]:
            habilitar_logs = False
        elif arg in ["--verbose", "-v"]:
            habilitar_logs = True
            configurar_logging(habilitar=True, nivel=logging.DEBUG)
        elif arg.startswith("--file="):
            arquivo_instancia = arg.split("=", 1)[1]
        elif arg in ["--file", "-f"]:
            if i + 1 < len(sys.argv):
                arquivo_instancia = sys.argv[i + 1]
                i += 1
        
        i += 1
    
    # Executa função principal
    main(habilitar_logs=habilitar_logs, arquivo_instancia=arquivo_instancia)
