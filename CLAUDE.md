# Futbol Quant Bot — Ruflo Agent Configuration
# Custodia Serrana Lab | Luis

## PROJECT CONTEXT
Sistema cuantitativo de detección de value bets en fútbol.
Stack: Python, Streamlit, Telegram Bot, Railway, GitHub.
Repo: custodiaserrana-lab/Sistema-de-Apuestas-deportivas

## MANDATORY RULES
- SIEMPRE ejecutar operaciones en paralelo (BatchTool)
- NUNCA modificar streamlit_app.py, app.py o main.py sin backup
- SIEMPRE mantener compatibilidad con Streamlit Cloud
- SIEMPRE usar encoding='utf-8-sig' para CSV de ARG/BRA
- SIEMPRE aplicar normalizar_columnas() antes de validar columnas

## SWARM TOPOLOGY
Usar topología HIERARCHICAL con 6 agentes especializados:

```
Coordinator (Queen)
├── Agent 1: Data Collector    → Descarga CSV football-data
├── Agent 2: Ratings Engine    → Calcula ratings históricos  
├── Agent 3: Value Detector    → Detecta value bets (EV > 3%)
├── Agent 4: Telegram Publisher → Publica señales + link afiliado
├── Agent 5: Tracker           → Registra resultados en Google Sheets
└── Agent 6: Optimizer         → Mejora el modelo continuamente
```

## AGENT INITIALIZATION
```
mcp__claude-flow__swarm_init {
  topology: "hierarchical",
  maxAgents: 6,
  strategy: "data_analysis"
}
```

## AGENT DEFINITIONS

### Agent 1 — Data Collector
```
mcp__claude-flow__agent_spawn {
  type: "specialist",
  name: "Data Collector",
  capabilities: ["csv_download", "data_validation", "football_data_co_uk"]
}
```
Tarea: Descargar semanalmente ARG.csv, BRA.csv, E0.csv, SP1.csv, I1.csv, D1.csv, F1.csv
URL base: https://www.football-data.co.uk/
Encoding: utf-8-sig (BOM removal para ARG/BRA)

### Agent 2 — Ratings Engine  
```
mcp__claude-flow__agent_spawn {
  type: "analyst",
  name: "Ratings Engine",
  capabilities: ["statistics", "time_series", "ratings_calculation"]
}
```
Tarea: Construir ratings por equipo usando últimos 6 partidos
Fórmula: rating = sum(FTHG - FTAG) últimos 6 partidos locales
         + sum(FTAG - FTHG) últimos 6 partidos visitante
Normalización columnas ARG/BRA: Home→HomeTeam, HG→FTHG, AG→FTAG, Res→FTR
                                  AvgCH→AvgH, PSCH→PSH, MaxCH→MaxH

### Agent 3 — Value Detector
```
mcp__claude-flow__agent_spawn {
  type: "analyst", 
  name: "Value Detector",
  capabilities: ["probability_modeling", "ev_calculation", "kelly_criterion"]
}
```
Motor probabilidades:
  p_L = 1.56 * x + 46.47
  p_V = 0.03 * x² - 1.27 * x + 23.65
  p_E = -0.03 * x² - 0.29 * x + 29.48
EV mínimo: 3%
Kelly Half: f = 0.5 × [(p×b - q) / b]
Bankroll base: 30.000 ARS

### Agent 4 — Telegram Publisher
```
mcp__claude-flow__agent_spawn {
  type: "specialist",
  name: "Telegram Publisher", 
  capabilities: ["telegram_api", "message_formatting", "affiliate_links"]
}
```
Chat ID: 5976165080
Bot ID: 8752280711
Token: desde variable TELEGRAM_TOKEN
Formato señal:
  ✅ VALUE BET
  ━━━━━━━━━━━━━━━━━━━━
  🏆 {liga}
  ⚽ {local} vs {visitante}
  🎯 {apuesta} — cuota: {cuota}
  📊 EV: +{edge}% | Kelly½: {kelly}%
  💵 Stake: ${stake_ars} ARS
  👉 Apostá: [Melbet](https://melbet.com/?ref=TUCODIGO)
  ━━━━━━━━━━━━━━━━━━━━

### Agent 5 — Tracker
```
mcp__claude-flow__agent_spawn {
  type: "specialist",
  name: "Results Tracker",
  capabilities: ["google_sheets", "roi_calculation", "performance_tracking"]
}
```
Sheet ID: desde variable SHEET_ID
Hoja: "Apuestas"
Columnas: fecha, liga, local, visitante, apuesta, cuota, stake_ars, 
          resultado, ganancia_ars, bankroll_post, edge, ev

### Agent 6 — Optimizer
```
mcp__claude-flow__agent_spawn {
  type: "optimizer",
  name: "Model Optimizer",
  capabilities: ["backtesting", "parameter_tuning", "performance_analysis"]
}
```
Tarea: Analizar yield histórico por liga y ajustar EDGE_MINIMO
       Si yield < 0 en 20+ apuestas → aumentar EDGE_MINIMO en 1%
       Si win_rate < 45% → revisar motor_probabilidades

## WEEKLY WORKFLOW (ejecutar cada lunes 06:00 ARG)
```
[BatchTool - Weekly Update]:
1. Agent 1: Descargar CSV actualizados de todas las ligas
2. Agent 2: Recalcular ratings con datos nuevos (paralelo por liga)
3. Agent 3: Detectar value bets para próximas 48h
4. Agent 4: Publicar señales en Telegram con links afiliado
5. Agent 5: Actualizar resultados de semana anterior en Sheets
6. Agent 6: Generar reporte ROI semanal
```

## MEMORY PATTERNS
```
memory_patterns: {
  "bot/ligas/ARG": "argentina_primera_division - 45 equipos - AvgCH odds",
  "bot/ligas/BRA": "brasil_serie_a - 38 equipos - AvgCH odds",  
  "bot/bankroll": "30000 ARS - Kelly Half - 1 unidad = 300 ARS",
  "bot/edge_minimo": "3.0% - ajustable por optimizer",
  "bot/telegram": "chat_id=5976165080 bot_id=8752280711",
  "bot/afiliado": "Melbet código personal - Mercado Pago CVU",
  "bot/deployment": "Streamlit Cloud + Railway (Telegram bot)"
}
```

## PERFORMANCE BENCHMARKS
- Velocidad objetivo: análisis 10 ligas < 30 segundos
- EV promedio mínimo aceptable: > 5%
- Win rate objetivo largo plazo: > 52%
- ROI objetivo: > 8% anual

## ARCHIVOS CRÍTICOS — NO MODIFICAR SIN BACKUP
- streamlit_app.py (UI principal)
- app.py (backtesting engine)  
- main.py (live detection engine)
- config/ligas.yaml (configuración ligas)

## COMANDOS ÚTILES
```bash
# Correr análisis manual
python main.py

# Correr backtesting
python app.py

# Deploy local Streamlit
streamlit run streamlit_app.py

# Instalar dependencias
pip install -r Requirements.txt
```
