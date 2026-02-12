# URBAN-NET-Database

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

## Postgres SQL

I can't connect the this database to the orion.

Change to the postgres database:

```bash
curl -iX POST 'http://localhost:1026/ngsi-ld/v1/subscriptions/' \
-H 'Content-Type: application/json' \
-d '{
  "description": "Notify Cygnus of Sensor changes",
  "type": "Subscription",
  "entities": [{"type": "Sensor"}],
  "notification": {
    "endpoint": {
      "uri": "http://urban-net-database-cygnus-1:5050/notify",
      "accept": "application/json"
    }
  }
}'
```

Trigger a Change
```bash
curl -iX PATCH 'http://localhost:1026/ngsi-ld/v1/entities/urn:ngsi-ld:Sensor:001/attrs' \
-H 'Content-Type: application/json' \
-d '{ "temperature": { "type": "Property", "value": 30.5 } }'
```


Enter the postgres databse

```bash
docker exec -it urban-net-database-postgres-1 psql -U myuser -d postgres
```