# 🚲 London Bikes — Big Data Dashboard

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat&logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-E25A1C?style=flat&logo=apachespark&logoColor=white)

End-to-end Big Data project on urban mobility and bike-sharing in London. Raw station data is ingested with **PySpark**, persisted in **MongoDB**, clustered with **K-Means**, and explored through an interactive **Streamlit** dashboard.

> ⚠️ The `archive/` folder (~2.3 GB of raw CSVs) is excluded from this repo. Download the dataset from [Kaggle — London's Rental Bicycle Network Usage](https://www.kaggle.com/datasets/ioexception/london-cycles/data) and place it in `archive/` before running the pipeline.

---

# Projeto Final - London Bikes

Ambiente dedicado ao projeto final de Big Data sobre mobilidade urbana e aluguer/utilizacao de bicicletas em Londres.

O projeto inclui ingestao e tratamento de dados com PySpark, persistencia em MongoDB, modelacao com K-Means e um dashboard Streamlit para exploracao interativa dos resultados.

## Estrutura

```text
Projeto_Final/
  archive/          # CSVs brutos descarregados do Kaggle ou manualmente
  data/             # dados auxiliares e parquet do projeto
  docker-compose.yml
  Dockerfile.jupyter
  requirements.txt  # dependencias Python para notebooks e dashboard
  notebooks/        # notebooks principais do projeto
  visualizations/   # mapas, graficos e HTMLs
  app.py            # dashboard Streamlit
```

## Componentes implementados

- `1-DataIngestion.ipynb`: ingestao dos CSVs de bicicletas e estacoes, com carga para Parquet e MongoDB.
- `2-DataUnderstanding.ipynb`: limpeza, enriquecimento temporal e separacao sazonal dos dados, preservando `query_time`, `Hour` e `Minute`.
- `3-StationsCleaning.ipynb`: limpeza e deduplicacao das estacoes, com criacao da collection `stations_clean`.
- `4-Modelling.ipynb`: clustering K-Means (`k=3`) sobre os dados de Verao, integracao com `stations_clean` e criacao da collection `bikes_modelled_summer`.
- `app.py`: dashboard Streamlit com filtros por data, hora, minuto e nivel de utilizacao, mapa Folium, grafico de distribuicao e tabela de estacoes.

## Arranque do ambiente

Na pasta `Projeto_Final`:

```powershell
docker compose up -d --build
```

Jupyter:

```text
http://localhost:8890
```

Dashboard Streamlit:

```text
http://localhost:8501
```

MongoDB a partir do Windows:

```text
mongodb://localhost:27018
```

MongoDB a partir dos notebooks:

```text
mongodb://mongodb:27017
```

## Dashboard Streamlit

O dashboard le dados diretamente do MongoDB, em particular da collection `bikes_modelled_summer`.

Para correr o dashboard dentro do container Jupyter:

```powershell
docker compose exec jupyter python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Funcionalidades disponiveis:

- seletor de data, hora e minuto
- filtro opcional por `nivel_utilizacao`
- mapa Folium com estacoes coloridas por nivel de utilizacao
- grafico de barras com distribuicao dos niveis
- tabela com detalhe das estacoes para a janela temporal escolhida

## Dependencias Python

As dependencias da componente Python estao centralizadas em `requirements.txt` e sao instaladas durante o `docker compose build`.

Incluem:

- `pymongo`
- `streamlit`
- `folium`

## Troubleshooting

Se o dashboard mostrar erro de ligacao ao MongoDB:

- confirmar que os containers estao ativos com `docker compose ps`
- confirmar que a base de dados arrancou antes do Streamlit
- testar a ligacao com `docker compose exec mongodb mongosh`

Se `app.py` arrancar mas nao aparecer nada no browser:

- confirmar que o comando foi executado com `--server.address 0.0.0.0 --server.port 8501`
- confirmar que a porta `8501` nao esta ocupada no host
- abrir manualmente `http://localhost:8501`

Se o mapa nao renderizar:

- reconstruir a imagem com `docker compose up -d --build`
- confirmar que `folium` foi instalado no container

Se houver alteracoes em `requirements.txt` ou `Dockerfile.jupyter`:

- reconstruir sempre os containers com `docker compose up -d --build`

## Acesso aos containers

Entrar no bash do Jupyter:

```powershell
docker compose exec jupyter bash
```

Dentro do bash do Jupyter, a pasta do projeto esta em:

```text
/home/jovyan/work
```

Entrar diretamente no MongoDB shell:

```powershell
docker compose exec mongodb mongosh
```

Alternativa usando o nome do container:

```powershell
docker exec -it projeto-final-mongodb mongosh
```

Entrar no bash do container MongoDB:

```powershell
docker exec -it projeto-final-mongodb bash
```

Depois, dentro do bash do MongoDB:

```bash
mongosh
```
