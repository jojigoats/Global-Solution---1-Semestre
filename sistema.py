"""
=============================================================
  SISTEMA DE MONITORAMENTO DE MISSÃO ESPACIAL - ARES-1
  Global Solution 2025 | FIAP
=============================================================
  Equipe: Julio sem amigos 
  Integrantes:
    - Julio Oliveira Joaquim - RM: 569113

=============================================================
"""

import csv       
import os       
import time      

# ─────────────────────────────────────────────────────────
#  UTILITÁRIOS DE EXIBIÇÃO
# ─────────────────────────────────────────────────────────

def linha(char="─", largura=60):
    """Imprime uma linha decorativa."""
    print(char * largura)

def titulo(texto):
    """Imprime um bloco de título formatado."""
    linha("═")
    print(f"  {texto}")
    linha("═")

def subtitulo(texto):
    """Imprime um subtítulo formatado."""
    linha()
    print(f"  ▶  {texto}")
    linha()

def digitar(texto, delay=0.012):
    """Imprime texto caractere por caractere (efeito terminal)."""
    for c in texto:
        print(c, end="", flush=True)
        time.sleep(delay)
    print()


# ─────────────────────────────────────────────────────────
#  1. LEITURA E CARREGAMENTO DOS DADOS (CSV)
# ─────────────────────────────────────────────────────────

def carregar_dados(caminho_csv):
    """
    Lê o arquivo CSV de telemetria e retorna uma lista de dicionários,
    um por linha. Estrutura: [{'tipo': ..., 'nome': ..., ...}, ...]

    Estrutura de dados: LISTA de DICIONÁRIOS
    Justificativa: permite acesso sequencial (lista) e por chave (dict).
    """
    dados_brutos = []  # lista principal de registros

    # Localiza o CSV relativo ao diretório deste script
    base = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(base, "..", caminho_csv)

    try:
        with open(caminho, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for linha_csv in reader:
                dados_brutos.append(dict(linha_csv))
    except FileNotFoundError:
        print(f"[ERRO] Arquivo '{caminho}' não encontrado.")
        print("       Verifique se data/dados.csv existe.")

    return dados_brutos


# ─────────────────────────────────────────────────────────
#  2. ORGANIZAÇÃO DOS DADOS EM ESTRUTURAS ESPECÍFICAS
# ─────────────────────────────────────────────────────────

def organizar_dados(dados_brutos):
    """
    Distribui os dados brutos em estruturas de dados adequadas:

      - modulos     → DICIONÁRIO (acesso O(1) por nome de módulo)
      - series_*    → LISTAS (séries temporais de energia)
      - matriz      → LISTA DE LISTAS / MATRIZ (horário × variável)
      - ambientais  → DICIONÁRIO (variáveis ambientais)
      - log_eventos → LISTA (log cronológico = fila de chegada)
      - pilha_criticos → LISTA usada como PILHA (LIFO)
      - inconsistencias → LISTA
    """

    # ── Dicionário de módulos críticos ──────────────────
    # Chave: nome do módulo | Valor: dict com status e dados
    modulos = {}

    # ── Listas de séries temporais ─────────────────────
    lista_geracao   = []   # kWh de geração solar por horário
    lista_consumo   = []   # kWh de consumo por horário
    lista_reserva   = []   # % de reserva por horário
    lista_horarios  = []   # horários correspondentes

    # ── Dicionário de variáveis ambientais ─────────────
    ambientais = {}

    # ── Lista de eventos (fila de chegada) ─────────────
    log_eventos = []   # FILA: primeiro a entrar, primeiro a sair

    # ── Pilha de eventos críticos ──────────────────────
    pilha_criticos = []   # PILHA: último adicionado = topo

    # ── Lista de inconsistências ───────────────────────
    inconsistencias = []

    # ── Hierarquia da missão (dicionário aninhado) ─────
    hierarquia = {
        "energia":  {"solar": None, "bateria": None, "reserva": None},
        "habitat":  {"oxigenio": None, "temperatura": None, "pressao": None},
        "comunicacao": {"qualidade": None, "status": None},
    }

    # Processa cada registro
    for reg in dados_brutos:
        tipo  = reg.get("tipo", "").strip()
        nome  = reg.get("nome", "").strip()
        valor = reg.get("valor", "").strip()
        hora  = reg.get("horario", "--").strip()

        # Módulos críticos → dicionário
        if tipo == "modulo":
            modulos[nome] = {
                "status": int(valor),        # 0 ou 1
                "status_texto": "OK" if int(valor) == 1 else "FALHA",
            }

        # Energia → listas + hierarquia
        elif tipo == "energia":
            val_float = float(valor)
            if nome == "geracao":
                lista_geracao.append(val_float)
                if hora not in lista_horarios:
                    lista_horarios.append(hora)
                hierarquia["energia"]["solar"] = val_float
            elif nome == "consumo":
                lista_consumo.append(val_float)
            elif nome == "reserva":
                lista_reserva.append(val_float)
                hierarquia["energia"]["bateria"] = val_float

        # Variáveis ambientais → dicionário + hierarquia
        elif tipo == "ambiental":
            try:
                ambientais[nome] = float(valor)
            except ValueError:
                ambientais[nome] = valor  # texto (ex.: "alta")

            # Preenche hierarquia de habitat e comunicação
            if nome == "temperatura_interna":
                hierarquia["habitat"]["temperatura"] = valor
            elif nome == "pressao_interna":
                hierarquia["habitat"]["pressao"] = valor
            elif nome == "qualidade_comunicacao":
                hierarquia["comunicacao"]["qualidade"] = valor

        # Log de eventos → fila (append = enqueue)
        elif tipo == "log":
            log_eventos.append({"horario": hora, "evento": valor})
            # Se for crítico, empilha também
            if "CRITICO" in valor.upper() or "ALERTA" in valor.upper():
                pilha_criticos.append({"horario": hora, "evento": valor})

        # Inconsistências → lista separada
        elif tipo == "inconsistencia":
            inconsistencias.append({
                "modulo": nome,
                "valor":  valor,
                "obs":    "Divergência entre status binário e sensor"
            })

    # Atualiza hierarquia com reserva final
    if lista_reserva:
        hierarquia["energia"]["reserva"] = lista_reserva[-1]
    if "qualidade_comunicacao" in ambientais:
        hierarquia["comunicacao"]["qualidade"] = ambientais["qualidade_comunicacao"]
    hierarquia["comunicacao"]["status"] = modulos.get("comunicacao", {}).get("status_texto", "?")
    hierarquia["habitat"]["oxigenio"]   = modulos.get("suporte_vida", {}).get("status_texto", "?")

    # ── Matriz: linhas = horários, colunas = [geração, consumo, reserva]
    # Estrutura: lista de listas [ [hora, ger, cons, res], ... ]
    n = min(len(lista_horarios), len(lista_geracao),
            len(lista_consumo),  len(lista_reserva))
    matriz_energia = []
    for i in range(n):
        matriz_energia.append([
            lista_horarios[i],
            lista_geracao[i],
            lista_consumo[i],
            lista_reserva[i],
        ])

    return {
        "modulos":         modulos,
        "lista_geracao":   lista_geracao,
        "lista_consumo":   lista_consumo,
        "lista_reserva":   lista_reserva,
        "lista_horarios":  lista_horarios,
        "matriz_energia":  matriz_energia,
        "ambientais":      ambientais,
        "log_eventos":     log_eventos,       # fila
        "pilha_criticos":  pilha_criticos,    # pilha
        "inconsistencias": inconsistencias,
        "hierarquia":      hierarquia,
    }


# ─────────────────────────────────────────────────────────
#  3. REGRAS LÓGICAS E DIAGNÓSTICO
# ─────────────────────────────────────────────────────────

def diagnosticar(dados):
    """
    Aplica regras lógicas (IF/ELIF/ELSE + AND/OR/NOT) para classificar
    o estado operacional da missão.

    Expressão booleana principal do diagnóstico:
      STATUS_CRITICO = (reserva < 30 AND consumo > geracao)
                    OR (comunicacao == FALHA AND radiacao == "alta")
                    OR (NOT suporte_vida)
                    OR (inconsistencia_detectada AND modulo_critico_afetado)

    Retorna uma lista de alertas com nível e recomendação.
    """

    modulos    = dados["modulos"]
    reserva    = dados["lista_reserva"][-1] if dados["lista_reserva"] else 100
    consumo    = dados["lista_consumo"][-1] if dados["lista_consumo"] else 0
    geracao    = dados["lista_geracao"][-1] if dados["lista_geracao"] else 0
    ambientais = dados["ambientais"]
    inconsist  = dados["inconsistencias"]

    alertas = []   # lista de alertas gerados

    # ── Extrai valores booleanos de módulos ─────────────
    suporte_vida = modulos.get("suporte_vida", {}).get("status", 0)
    comunicacao  = modulos.get("comunicacao",  {}).get("status", 0)
    energia_mod  = modulos.get("energia",      {}).get("status", 0)
    habitat      = modulos.get("habitat",      {}).get("status", 0)
    laboratorio  = modulos.get("laboratorio",  {}).get("status", 0)

    # Variáveis ambientais
    radiacao   = str(ambientais.get("radiacao",              "baixa")).lower()
    qual_com   = float(ambientais.get("qualidade_comunicacao", 100))
    temp_int   = float(ambientais.get("temperatura_interna",   20))
    pressao    = float(ambientais.get("pressao_interna",       101.3))

    # ── REGRA 1: Suporte à Vida ──────────────────────────
    # Expressão: NOT suporte_vida
    if not suporte_vida:
        alertas.append({
            "nivel":    "CRITICO",
            "modulo":   "suporte_vida",
            "mensagem": "Módulo de suporte à vida INATIVO.",
            "recomendacao": "AÇÃO IMEDIATA: Acionar sistema de backup de oxigênio."
        })

    # ── REGRA 2: Energia Crítica ─────────────────────────
    # Expressão: reserva < 30 AND consumo > geracao
    if reserva < 30 and consumo > geracao:
        alertas.append({
            "nivel":    "CRITICO",
            "modulo":   "energia",
            "mensagem": f"Reserva em {reserva:.0f}% com consumo ({consumo} kWh) "
                        f"excedendo geração ({geracao} kWh).",
            "recomendacao": "Desligar laboratório e sistemas não essenciais; "
                            "redirecionar energia ao habitat."
        })
    elif reserva < 40 and not energia_mod:
        # Expressão: reserva < 40 AND NOT energia_mod
        alertas.append({
            "nivel":    "ALERTA",
            "modulo":   "energia",
            "mensagem": f"Reserva em {reserva:.0f}% e módulo de energia com falha.",
            "recomendacao": "Reduzir consumo imediatamente e verificar painéis solares."
        })
    elif reserva < 50:
        # Expressão: reserva < 50
        alertas.append({
            "nivel":    "ALERTA",
            "modulo":   "energia",
            "mensagem": f"Reserva energética em {reserva:.0f}% — abaixo do ideal.",
            "recomendacao": "Monitorar consumo e reduzir cargas secundárias."
        })

    # ── REGRA 3: Comunicação + Radiação ─────────────────
    # Expressão: NOT comunicacao OR (radiacao == "alta" AND qual_com < 40)
    if (not comunicacao) or (radiacao == "alta" and qual_com < 40):
        alertas.append({
            "nivel":    "CRITICO",
            "modulo":   "comunicacao",
            "mensagem": f"Comunicação instável — qualidade em {qual_com:.0f}%, "
                        f"radiação {radiacao}.",
            "recomendacao": "Ativar canal de emergência; aguardar janela de baixa radiação."
        })
    elif qual_com < 60:
        alertas.append({
            "nivel":    "ALERTA",
            "modulo":   "comunicacao",
            "mensagem": f"Qualidade de comunicação degradada: {qual_com:.0f}%.",
            "recomendacao": "Checar antenas e reduzir interferências internas."
        })

    # ── REGRA 4: Radiação Elevada ────────────────────────
    # Expressão: radiacao == "alta" AND (NOT habitat OR pressao < 95)
    if radiacao == "alta" and (not habitat or pressao < 95):
        alertas.append({
            "nivel":    "CRITICO",
            "modulo":   "habitat",
            "mensagem": f"Radiação ALTA com habitat comprometido (pressão {pressao} kPa).",
            "recomendacao": "Mover tripulação para abrigo blindado; checar vedação."
        })
    elif radiacao == "alta":
        alertas.append({
            "nivel":    "ALERTA",
            "modulo":   "habitat",
            "mensagem": "Radiação elevada detectada. Habitat operacional.",
            "recomendacao": "Reduzir EVA; monitorar dosimetria dos astronautas."
        })

    # ── REGRA 5: Temperatura Interna ────────────────────
    # Expressão: temp_int < 18 OR temp_int > 28
    if temp_int < 18 or temp_int > 28:
        alertas.append({
            "nivel":    "ALERTA",
            "modulo":   "habitat",
            "mensagem": f"Temperatura interna fora da faixa segura: {temp_int}°C.",
            "recomendacao": "Verificar sistema de controle térmico do habitat."
        })

    # ── REGRA 6: Inconsistência de sensor ───────────────
    # Expressão: len(inconsist) > 0 AND laboratorio == 1
    if len(inconsist) > 0 and laboratorio == 1:
        alertas.append({
            "nivel":    "ALERTA",
            "modulo":   "laboratorio",
            "mensagem": "Inconsistência detectada: módulo reporta OK mas sensor acusou FALHA.",
            "recomendacao": "Realizar verificação manual dos sensores do laboratório."
        })

    # Ordenar alertas: CRITICO primeiro, depois ALERTA, depois NORMAL
    ordem = {"CRITICO": 0, "ALERTA": 1, "NORMAL": 2}
    alertas.sort(key=lambda a: ordem.get(a["nivel"], 9))

    return alertas


# ─────────────────────────────────────────────────────────
#  4. ANÁLISE E PREVISÃO (REGRESSÃO LINEAR MANUAL)
# ─────────────────────────────────────────────────────────

def regressao_linear(xs, ys):
    """
    Calcula coeficientes da reta y = a*x + b usando mínimos quadrados.
    Implementação manual — sem bibliotecas externas.

      a = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
      b = (Σy - a*Σx) / n
    """
    n = len(xs)
    if n < 2:
        return 0, ys[0] if ys else 0

    soma_x   = sum(xs)
    soma_y   = sum(ys)
    soma_xy  = sum(xs[i] * ys[i] for i in range(n))
    soma_x2  = sum(x**2 for x in xs)

    denominador = n * soma_x2 - soma_x ** 2
    if denominador == 0:
        return 0, soma_y / n   # linha horizontal

    a = (n * soma_xy - soma_x * soma_y) / denominador
    b = (soma_y - a * soma_x) / n
    return a, b


def prever_reserva(dados):
    """
    Usa regressão linear na série histórica da reserva energética para
    estimar o valor no próximo ciclo (índice n+1).

    A previsão influencia diretamente as recomendações do sistema.

    Retorna: dicionário com dados da análise.
    """
    reserva = dados["lista_reserva"]

    xs = list(range(len(reserva)))          # [0, 1, 2, 3, 4, 5]
    ys = reserva                            # [60, 50, 40, 32, 28, 22]

    a, b = regressao_linear(xs, ys)

    proximo_ciclo = len(reserva)            # índice do próximo ponto
    previsao      = a * proximo_ciclo + b   # valor previsto

    # Calcula a taxa de variação média
    variacoes = [ys[i+1] - ys[i] for i in range(len(ys)-1)]
    media_var = sum(variacoes) / len(variacoes) if variacoes else 0

    # Quantos ciclos até esgotar (reserva ≤ 0)?
    ciclos_restantes = int(-b / a) - proximo_ciclo if a < 0 else None

    return {
        "historico":        list(zip(xs, ys)),
        "coeficiente_a":    round(a, 4),
        "coeficiente_b":    round(b, 4),
        "previsao":         round(previsao, 2),
        "media_variacao":   round(media_var, 2),
        "ciclos_restantes": ciclos_restantes,
    }


# ─────────────────────────────────────────────────────────
#  5. FUNÇÕES DE EXIBIÇÃO
# ─────────────────────────────────────────────────────────

def exibir_cabecalho():
    titulo("SISTEMA ARES-1 — MONITORAMENTO DE MISSÃO ESPACIAL")
    print("  Status: ONLINE  |  Leitura de telemetria iniciada")
    print()


def exibir_modulos(modulos):
    subtitulo("STATUS DOS MÓDULOS CRÍTICOS")
    print(f"  {'MÓDULO':<20} {'STATUS':<8} {'BINÁRIO'}")
    linha("-")
    for nome, dados in modulos.items():
        icone = "✔" if dados["status"] == 1 else "✘"
        cor   = "[ OK ]" if dados["status"] == 1 else "[FALHA]"
        print(f"  {nome:<20} {cor:<8}  {icone}  ({dados['status']})")
    print()


def exibir_matriz_energia(matriz):
    subtitulo("MATRIZ DE ENERGIA (Horário × Variável)")
    print(f"  {'HORÁRIO':<8} {'GERAÇÃO (kWh)':>14} {'CONSUMO (kWh)':>14} {'RESERVA (%)':>12}")
    linha("-")
    for row in matriz:
        hora, ger, cons, res = row
        indicador = "▼" if cons > ger else "▲"
        print(f"  {hora:<8} {ger:>14.1f} {cons:>14.1f} {res:>11.1f}%  {indicador}")
    print()


def exibir_ambientais(amb):
    subtitulo("VARIÁVEIS AMBIENTAIS")
    for k, v in amb.items():
        if isinstance(v, float):
            print(f"  {k:<28}: {v:.2f}")
        else:
            print(f"  {k:<28}: {v}")
    print()


def exibir_hierarquia(h):
    subtitulo("HIERARQUIA DA MISSÃO")
    for categoria, subitens in h.items():
        print(f"  ├─ {categoria.upper()}")
        for sub, val in subitens.items():
            print(f"  │    └─ {sub:<18}: {val}")
    print()


def exibir_log(fila):
    subtitulo("LOG DE EVENTOS (Fila — ordem de chegada)")
    for i, ev in enumerate(fila):
        prefixo = "⚠ " if ("ALERTA" in ev["evento"].upper()
                            or "CRITICO" in ev["evento"].upper()) else "  "
        print(f"  [{i+1:02d}] {ev['horario']:<6}  {prefixo}{ev['evento']}")
    print()


def exibir_pilha_criticos(pilha):
    subtitulo("PILHA DE EVENTOS CRÍTICOS (topo = mais recente)")
    if not pilha:
        print("  Nenhum evento crítico registrado.")
    else:
        for ev in reversed(pilha):   # exibe do topo à base
            print(f"  ▲ [{ev['horario']}] {ev['evento']}")
    print()


def exibir_inconsistencias(incs):
    subtitulo("INCONSISTÊNCIAS DETECTADAS")
    if not incs:
        print("  Nenhuma inconsistência encontrada.")
    else:
        for inc in incs:
            print(f"  ⚠  Módulo: {inc['modulo']}")
            print(f"     Valor registrado: {inc['valor']}")
            print(f"     Observação: {inc['obs']}")
    print()


def exibir_alertas(alertas):
    titulo("DIAGNÓSTICO E ALERTAS AUTOMÁTICOS")

    if not alertas:
        print("  ✔  Missão em condições NORMAIS. Nenhum alerta ativo.")
        return

    # Define o status global da missão
    niveis = [a["nivel"] for a in alertas]
    if "CRITICO" in niveis:
        status_global = "⚠  CRÍTICO"
    elif "ALERTA" in niveis:
        status_global = "⚡ ALERTA"
    else:
        status_global = "✔  NORMAL"

    print(f"  STATUS GLOBAL DA MISSÃO: {status_global}")
    print()

    for i, alerta in enumerate(alertas, 1):
        borda = "!!!" if alerta["nivel"] == "CRITICO" else "---"
        print(f"  {borda} ALERTA #{i} [{alerta['nivel']}] — Módulo: {alerta['modulo'].upper()}")
        print(f"       {alerta['mensagem']}")
        print(f"  ►  RECOMENDAÇÃO: {alerta['recomendacao']}")
        print()


def exibir_previsao(prev):
    subtitulo("ANÁLISE E PREVISÃO — REGRESSÃO LINEAR DA RESERVA ENERGÉTICA")

    print("  Dados históricos utilizados:")
    print(f"  {'Ciclo':>6}  {'Reserva (%)':>12}")
    linha("-", 30)
    for x, y in prev["historico"]:
        print(f"  {x:>6}  {y:>12.1f}")

    print()
    print(f"  Equação da reta:  y = {prev['coeficiente_a']}x + {prev['coeficiente_b']:.2f}")
    print(f"  Variação média por ciclo: {prev['media_variacao']:.2f}%")
    print(f"  ► Previsão para o próximo ciclo: {prev['previsao']:.1f}%")

    if prev["ciclos_restantes"] is not None and prev["ciclos_restantes"] > 0:
        print(f"  ⚠  Estimativa: reserva se esgota em ~{prev['ciclos_restantes']} ciclo(s).")
    elif prev["previsao"] <= 0:
        print("  ⚠  CRÍTICO: reserva poderá se esgotar antes do próximo ciclo!")

    print()
    print("  Influência na decisão:")
    if prev["previsao"] < 15:
        print("  → CRÍTICO: acionar protocolo de emergência energética imediata.")
    elif prev["previsao"] < 25:
        print("  → ALERTA: reduzir consumo e priorizar sistemas vitais.")
    else:
        print("  → Monitorar. Reserva ainda dentro de margem operacional.")
    print()


# ─────────────────────────────────────────────────────────
#  6. FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────

def main():
    exibir_cabecalho()

    # ── Carrega e organiza os dados ──────────────────────
    dados_brutos = carregar_dados("data/dados.csv")
    if not dados_brutos:
        print("[ERRO] Nenhum dado carregado. Encerrando.")
        return

    dados = organizar_dados(dados_brutos)

    # ── Exibe estruturas de dados ────────────────────────
    exibir_modulos(dados["modulos"])
    exibir_matriz_energia(dados["matriz_energia"])
    exibir_ambientais(dados["ambientais"])
    exibir_hierarquia(dados["hierarquia"])
    exibir_log(dados["log_eventos"])
    exibir_pilha_criticos(dados["pilha_criticos"])
    exibir_inconsistencias(dados["inconsistencias"])

    # ── Diagnóstico lógico ───────────────────────────────
    alertas = diagnosticar(dados)
    exibir_alertas(alertas)

    # ── Análise preditiva ────────────────────────────────
    previsao = prever_reserva(dados)
    exibir_previsao(previsao)

    linha("═")
    print("  FIM DO RELATÓRIO — SISTEMA ARES-1")
    linha("═")


# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
