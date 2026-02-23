# URBAN-NET-Database

## WEBSITE
Start the project

```bash
docker-compose up --build
```

LINK: http://localhost:8501


## Mongo DB
First comand:

```bash
curl -iX POST 'http://localhost:1026/ngsi-ld/v1/entities' \
-H 'Content-Type: application/json' \
-d '{
  "id": "urn:ngsi-ld:Sensor:001",
  "type": "Sensor",
  "temperature": {
    "type": "Property",
    "value": 25.5
  }
}'
```

Verify:
```bash
curl -X GET 'http://localhost:1026/ngsi-ld/v1/entities/urn:ngsi-ld:Sensor:001'
```

Update the database:

```bash
curl -iX PATCH 'http://localhost:1026/ngsi-ld/v1/entities/urn:ngsi-ld:Sensor:001/attrs' -H 'Content-Type: application/json' -d '{
  "temperature": {
    "type": "Property",
    "value": 28.2
  }
}'
```

Verify Update:
```bash
curl -X GET 'http://localhost:1026/ngsi-ld/v1/entities/urn:ngsi-ld:Sensor:001'
```

See the data in the MongoDB

```bash
# 1. Access the Mongo container (replace 'mongo' with your actual container name if different)
docker exec -it $(docker ps -qf "name=mongo") mongo

# 2. Inside the Mongo shell, switch to the Orion database
use orion

# 3. Find your entities
db.entities.find().pretty()
```

## Timesacle DB

Change to the postgres database and Trigger a Change:

```bash
curl http://localhost:8668/v2/notify -i -H 'Content-Type: application/json' -d @- <<EOF
{ 
    "subscriptionId": "5ce3dbb331dfg9h71aad5deeaa", 
    "data": [ 
        { 
            "id": "Room1", 
            "temperature": { "value": "10", "type": "Number" }, 
            "pressure": { "value": "12", "type": "Number" }, 
            "type": "Room" 
        } 
    ] 
}
EOF
```

See the change on QuantumLeap API:

```bash
curl -X GET "http://localhost:8668/v2/entities/Room1"
```

Query TimescaleDB Directly:

```bash
#Enter the TimescaleDB container
docker compose exec timescale psql -U postgres -d postgres

#List the tables
\dt

#Query the table
SELECT * FROM etroom;
```