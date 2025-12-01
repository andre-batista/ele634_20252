# Solução do Grupo Djavan – ELE634 (2025/2)

## 📝 Descrição

Este diretório contém a solução desenvolvida pelo **grupo Djavan** para o problema proposto na disciplina **ELE634 – Laboratório de Sistemas II**, ofertada no semestre **2025/2** na Universidade Federal de Minas Gerais.

O objetivo do trabalho é implementar heurísticas e estruturas de busca para resolver o *Problema de Embarque Remoto em Aeroportos*, envolvendo roteamento de ônibus, janelas de tempo, tempos máximos de viagem e restrições operacionais.  
A solução inclui:
- estruturas de dados otimizadas para representar instâncias;
- geração e manipulação de soluções factíveis;
- heurísticas e metaheurísticas (VND, VNS, movimentos locais);
- ferramentas auxiliares de avaliação e depuração.

---

## 📂 Estrutura do Projeto

A seguir está a estrutura de diretórios esperada para este projeto:

📁 projeto/
├── README.md
├── dados.py        # Carregamento e representação das instâncias
├── djavan.py       # Implementação da heurística principal e de resolva()
├── solucao.py      # Estrutura de representação de rotas e soluções
├── notebook.ipynb  # Exemplo de uso

## 📦 Dependências

O programa djavan.py utiliza as seguintes bibliotecas Python:

- **random**
- **hashlib**
- **numpy**
- **pandas**

Além destes, ele utiliza os scripts dados.py e solucao.py, fornecidos para a disciplina;

O arquivo notebook.ipynb adicionalmente utiliza as seguintes bibliotecas Python:


- **jupyter**
- **matplotlib**
- **seaborn**

Além destes, ele utiliza o script solucao.py, fornecido para a disciplina;

## ▶️ Como usar

O script djavan.py possui o método resolva(dados, numero_avaliacoes) com assinatura conforme a especificação solicitada na disciplina. As outras funções contidas no arquivo são chamadas por este método.

O arquivo notebook.ipynb contém um exemplo de uso do script djavan.py, já configurado para a bateria de testes esperada do modelo construído.
