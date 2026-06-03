# URBAN-NET-Database

A collection of utilities and example data for ingesting urban mobility and environmental datasets into databases (MongoDB and TimescaleDB). Includes parsers for CSV, GeoJSON and GTFS, data converters, and scripts to send data to target databases or NGSI-LD endpoints.

## Features
- Parsers: CSV, GeoJSON, GTFS
- Converters: convert to NGSI-LD / JSON formats
- Senders: send data to MongoDB, TimescaleDB, or NGSI-LD
- Example data and small utilities for testing and local development

## Requirements
- Python 3.8+ (3.9+ recommended)
- pip
- Docker & docker-compose (for running local DBs and brokers)

Install Python dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

## Quick start

1. Start services (optional) — run local DBs / broker with docker-compose:

```bash
docker-compose up -d
```

2. Run a parser or sender script from the `backend` folder. Examples:

```bash
# convert example GTFS -> JSON
python backend/parserGTFS.py

# send example data to MongoDB
python backend/sendDataMongoDB.py

# send example data to TimescaleDB
python backend/sendDataTimescaleDB.py
```

See individual script docstrings and `backend` source files for available CLI options and usage.

## Project layout

- `backend/` — Python scripts and parsers (parserCSV.py, parserGeoJSON.py, parserGTFS.py, sendDataMongoDB.py, sendDataTimescaleDB.py, etc.)
- `data/` — curated example JSON datasets
- `dataCSV/`, `dataGeoJSON/`, `dataGTFS/` — raw input datasets and converted outputs
- `output/` — exported conversion examples
- `docker-compose.yml`, `Dockerfile`, `mosquitto.conf` — local infrastructure and broker config

## Common workflows

- To convert CSV/GTFS/GeoJSON to NGSI-LD-like JSON, run the corresponding parser in `backend/` and inspect the generated files under `output/` or `dataCSV_JSON/`.
- To push converted data to a database, configure the connection parameters in the related sender script (or environment variables) and run the sender scripts in `backend/`.

## Testing and examples
- Example test files are located under `data/` and `dataCSV/dataCSV_JSON/` — use them to exercise the parsers and senders.

## Contributing
Contributions, bug reports and feature requests are welcome. Please open an issue or submit a PR with a clear description and minimal reproduction steps.

## License & Contact
This repository does not include a license file. Contact the maintainer for reuse or distribution questions.

For questions or help, open an issue or contact the project owner.
