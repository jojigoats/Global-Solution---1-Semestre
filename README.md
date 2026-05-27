# 🚀 ARES-1 — Sistema de Monitoramento de Missão Espacial

> Global Solution 2025 | FIAP — Ciência da Computação  
> Tema: Indústria Espacial

---

## 👥 Equipe

| Nome | RM |
|------|----|
| Julio Oliveira Joaquim | 569113 |

---

## 📋 Resumo do Problema

A missão espacial experimental **ARES-1** enfrenta uma situação crítica: queda contínua na reserva energética, falha no módulo de comunicação e radiação elevada. O sistema desenvolvido lê dados de telemetria, organiza-os em estruturas computacionais adequadas, aplica regras lógicas para classificar o estado da missão, emite alertas automáticos priorizados e prevê o comportamento futuro da reserva energética por meio de regressão linear manual.

**Cenário analisado:**
- Reserva energética em 22% e caindo
- Módulo de comunicação offline (status binário = 0)
- Radiação externa em nível **alto**
- Inconsistência detectada no módulo de laboratório (sensor vs. status)

---

## 🗂️ Estruturas de Dados Utilizadas

| Estrutura | Onde foi usada | Justificativa |
|-----------|---------------|---------------|
| **Lista** | Séries de geração, consumo e reserva de energia ao longo do tempo | Permite acesso por índice e iteração sequencial para cálculos de previsão |
| **Fila** (lista com append/FIFO) | Log de eventos em ordem cronológica | Registra eventos na ordem de chegada, respeitando a lógica temporal |
| **Pilha** (lista com LIFO) | Eventos críticos e de alerta | O evento mais recente fica no topo, permitindo acesso rápido à última ocorrência crítica |
| **Dicionário** | Status dos módulos críticos e variáveis ambientais | Acesso O(1) pelo nome do módulo, ideal para consultas rápidas em tempo real |
| **Hierarquia** (dicionário aninhado) | Relações entre subsistemas (energia → solar/bateria; habitat → O₂/temperatura) | Representa a árvore de dependências da missão de forma legível |
| **Matriz** (lista de listas) | Leituras de energia por horário × variável | Organiza dados multidimensionais com acesso por [linha][coluna] |

---

## ⚙️ Regras Lógicas Principais

**Expressão booleana principal do diagnóstico:**

```
STATUS_CRITICO = (reserva < 30 AND consumo > geracao)
              OR (NOT comunicacao OR (radiacao == "alta" AND qualidade < 40))
              OR (NOT suporte_vida)
              OR (len(inconsistencias) > 0 AND laboratorio == 1)
```

| Regra | Condição | Nível | Ação |
|-------|----------|-------|------|
| R1 | `NOT suporte_vida` | CRÍTICO | Acionar backup de oxigênio |
| R2 | `reserva < 30 AND consumo > geracao` | CRÍTICO | Desligar sistemas não essenciais |
| R3 | `reserva < 40 AND NOT energia_mod` | ALERTA | Reduzir consumo imediatamente |
| R4 | `NOT comunicacao OR (radiacao=="alta" AND qual_com < 40)` | CRÍTICO | Canal de emergência |
| R5 | `radiacao == "alta" AND (NOT habitat OR pressao < 95)` | CRÍTICO | Mover tripulação para abrigo |
| R6 | `temp_int < 18 OR temp_int > 28` | ALERTA | Verificar controle térmico |
| R7 | `len(inconsist) > 0 AND laboratorio == 1` | ALERTA | Verificação manual dos sensores |

---

## 📈 Técnica de Previsão

**Técnica:** Regressão Linear por Mínimos Quadrados (implementação manual)

**Variável analisada:** Reserva energética (%) ao longo de 6 ciclos

**Dados utilizados:**

| Ciclo | Reserva (%) |
|-------|------------|
| 0 (06:00) | 60.0 |
| 1 (09:00) | 50.0 |
| 2 (12:00) | 40.0 |
| 3 (15:00) | 32.0 |
| 4 (18:00) | 28.0 |
| 5 (21:00) | 22.0 |

**Resultado:**
- Equação: `y = -7.54x + 57.52`
- **Previsão para o ciclo 6: ~12.3%**
- Taxa média de queda: **-7.6% por ciclo**
- Estimativa de esgotamento: **~1 ciclo**

**Influência na decisão:** A previsão abaixo de 15% aciona automaticamente o protocolo de emergência energética.

---

## ▶️ Como Executar

**Pré-requisito:** Python 3.8 ou superior instalado.

```bash
# Clone o repositório
git clone https://github.com/[usuario]/[repositorio].git
cd [repositorio]

# Execute o sistema
python src/sistema.py
```

Não são necessárias bibliotecas externas. O arquivo `data/dados.csv` deve estar presente.

---

## 📥 Exemplo de Entrada

```
Arquivo: data/dados.csv

modulo,comunicacao,0,bool,--        → Módulo de comunicação INATIVO
energia,reserva,22,percent,21:00   → Reserva em 22%
ambiental,radiacao,alta,nivel,--   → Radiação elevada
```

## 📤 Exemplo de Saída

```
STATUS GLOBAL DA MISSÃO: ⚠  CRÍTICO

!!! ALERTA #1 [CRITICO] — Módulo: ENERGIA
    Reserva em 22% com consumo (65.0 kWh) excedendo geração (10.0 kWh).
►  RECOMENDAÇÃO: Desligar laboratório e sistemas não essenciais;
                 redirecionar energia ao habitat.

!!! ALERTA #2 [CRITICO] — Módulo: COMUNICACAO
    Comunicação instável — qualidade em 35%, radiação alta.
►  RECOMENDAÇÃO: Ativar canal de emergência; aguardar janela de baixa radiação.

► Previsão para o próximo ciclo: 12.3%
→ CRÍTICO: acionar protocolo de emergência energética imediata.
```

---

## 📌 Recomendações Geradas pelo Sistema

1. **(CRÍTICO)** Desligar laboratório e sistemas não essenciais; redirecionar energia ao habitat e carregamento de baterias.
2. **(CRÍTICO)** Ativar canal de comunicação de emergência; aguardar janela de baixa radiação para restabelecer link.
3. **(ALERTA)** Reduzir atividades externas (EVA); monitorar dosimetria dos astronautas.
4. **(ALERTA)** Realizar verificação manual dos sensores do laboratório (inconsistência detectada).

---

## 🎥 Vídeo de Apresentação

[Link do vídeo no YouTube — Não Listado](https://youtube.com/...)

---

## 🧠 Conclusões e Aprendizados

O projeto demonstrou como estruturas de dados clássicas (listas, filas, pilhas, dicionários e matrizes) se aplicam diretamente a problemas reais de engenharia de sistemas. A regressão linear manual evidenciou que é possível implementar análise preditiva sem depender de frameworks externos, compreendendo os fundamentos matemáticos. A organização modular do código — com funções separadas para leitura, organização, diagnóstico, previsão e exibição — facilitou a colaboração em equipe e a manutenção do sistema.

O desafio mais significativo foi tratar a inconsistência proposital no módulo de laboratório, que ensinou a importância de validação cruzada de dados em sistemas críticos onde uma única leitura incorreta pode comprometer uma decisão.
