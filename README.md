# URBAN-NET-Database

## WEBSITE
Start the project

```bash
docker-compose up --build -d
```

LINK: http://localhost:8501


Stop the project
```bash
docker-compose down -v
```

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

## Login (Keycloak)

1. Go to http://localhost:8080 and log in with the credentials admin / admin.

2. Create a Realm: Hover over the "master" realm in the top-left dropdown and click Create Realm. Name it fiware-realm.

3. Create a Client: * Go to Clients -> Create client.

  - Client ID: streamlit-app

  - Click Next. Ensure "Standard flow" (OAuth2) is enabled.

  - Click Next.

  - Valid redirect URIs: http://localhost:8501/* (This is crucial; it tells Keycloak it's safe to send tokens back to your Streamlit UI).

  - Web origins: http://localhost:8501

  - Click Save.

4. Create a User:

  - Go to Users -> Add user. Set a username (e.g., testuser) and click Create.

  - Go to the Credentials tab for that user, click Set password, type a password, and toggle "Temporary" to Off.

5. Create a Role:

  - Created a Realm Role named admin.

  - Assigned that admin role to your test user.

  - Ensured that Client Scopes -> roles -> Mappers -> realm roles is configured to add the realm roles to the Access Token. (This is usually configured this way by default in modern Keycloak versions).

### How to enable the register:

1. Log in to your Keycloak Admin Console (e.g., http://localhost:8080).

2. Select your realm (fiware-realm).

3. On the left sidebar, go to Realm Settings.

4. Click on the Login tab.

5. Toggle User registration to ON.

6. Save your changes.


## Grafana (Visualization)

Once the container is running, open your browser and go to http://localhost:3000. 

1. Log in with admin / admin. 

2. Now, you need to link Grafana to your database. In the left-hand menu, go to Connections -> Data sources.

3. Click Add data source and search for PostgreSQL.

4. Fill in the connection details using the internal Docker network names from your compose file:
  - Host: timescale:5432

  - Database: postgres 

  - User: postgres

  - Password: password

  - TLS/SSL Mode: disable

5. Under the PostgreSQL details section, make sure to enable the TimescaleDB toggle.

6. Click Save & test. You should get a green notification saying the database connection is okay.

To read the geoJson type data, this examples will help:

```sql
  -- As human-readable text (WKT format)
  SELECT ST_AsText(location) FROM etgtfsstop;
  -- Result: POINT(-8.57522842559986 41.2098796212627)

  -- As GeoJSON
  SELECT ST_AsGeoJSON(location) FROM etgtfsstop;
  -- Result: {"type":"Point","coordinates":[-8.575228425599860,41.209879621262700]}

  -- As latitude/longitude separately
  SELECT 
    ST_X(location) AS longitude,
    ST_Y(location) AS latitude
  FROM etgtfsstop;
```
## Mosquitto / IoT Agent

```bash
curl -iX POST \
  'http://localhost:4041/iot/services' \
  -H 'Content-Type: application/json' \
  -H 'fiware-service: openiot' \
  -H 'fiware-servicepath: /' \
  -d '{
    "services": [{
      "apikey": "my-secret-key",
      "cbroker": "http://orion:1026",
      "entity_type": "Sensor",
      "resource": "/iot/json"
    }]
  }'
```

```bash
curl -iX POST \
  'http://localhost:4041/iot/devices' \
  -H 'Content-Type: application/json' \
  -H 'fiware-service: openiot' \
  -H 'fiware-servicepath: /' \
  -d '{
    "devices": [{
      "device_id": "sensor001",
      "entity_name": "urn:ngsi-ld:Sensor:001",
      "entity_type": "Sensor",
      "protocol": "IoTA-JSON",
      "transport": "MQTT",
      "apikey": "my-secret-key",
      "attributes": [
        { "object_id": "t", "name": "temperature", "type": "Property" }
      ]
    }]
  }'
```

```bash
curl -iX POST \
  'http://localhost:1026/ngsi-ld/v1/subscriptions/' \
  -H 'Content-Type: application/ld+json' \
  -H 'fiware-service: openiot' \
  -H 'fiware-servicepath: /' \
  -d '{
  "description": "Notify QuantumLeap of temperature changes",
  "type": "Subscription",
  "entities": [{"type": "Sensor"}],
  "watchedAttributes": ["temperature"],
  "notification": {
    "attributes": ["temperature"],
    "format": "normalized",
    "endpoint": {
      "uri": "http://quantumleap:8668/v2/notify",
      "accept": "application/json"
    }
  },
  "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
}'
```

```bash
# Publish MQTT message
docker exec -it urban-net-database-mosquitto-1 \
  mosquitto_pub -h localhost \
  -t "/my-secret-key/sensor001/attrs" \
  -m '{"t": 24.5}'

# Wait 2-3 seconds, then query Orion
curl -X GET \
  'http://localhost:1026/ngsi-ld/v1/entities/urn:ngsi-ld:Sensor:001' \
  -H 'NGSILD-Tenant: openiot' \ 
  -H 'Accept: application/ld+json'
```

### Test for real time case

1. Step 1 — Provision service
  - This step groups your devices together. You can leave the resource and context broker as their defaults.

  - API key: traffic-key (or any unique string, just be consistent)

  - Entity type: TrafficFlowObserved

  - Resource: /iot/json

  - Context broker: http://orion:1026

2. Step 2 — Provision device
  - This maps the simple JSON keys coming from your MQTT device (object_id) to the formal NGSI-LD attributes (name). We will use identical names for simplicity.

  - Device ID: traffic001

  - Entity name: urn:ngsi-ld:TrafficFlowObserved:9577808

  - Entity type: TrafficFlowObserved

  - API key: traffic-key (must exactly match Step 1)

  - Attributes (JSON list): Copy and paste the following block:
  ```json
  [
    {"object_id": "dateObserved", "name": "dateObserved", "type": "Property"},
    {"object_id": "equipmentId", "name": "equipmentId", "type": "Property"},
    {"object_id": "laneDirection", "name": "laneDirection", "type": "Property"},
    {"object_id": "intensity", "name": "intensity", "type": "Property"},
    {"object_id": "averageVehicleSpeed", "name": "averageVehicleSpeed", "type": "Property"},
    {"object_id": "occupancy", "name": "occupancy", "type": "Property"},
    {"object_id": "AGG_ID", "name": "AGG_ID", "type": "Property"},
    {"object_id": "AGG_PERIOD_LEN_MINS", "name": "AGG_PERIOD_LEN_MINS", "type": "Property"},
    {"object_id": "NR_LANES", "name": "NR_LANES", "type": "Property"},
    {"object_id": "AVG_SPEED_HARMONIC", "name": "AVG_SPEED_HARMONIC", "type": "Property"},
    {"object_id": "AVG_LENGTH", "name": "AVG_LENGTH", "type": "Property"},
    {"object_id": "AVG_SPACING", "name": "AVG_SPACING", "type": "Property"},
    {"object_id": "LIGHT_VEHICLE_RATE", "name": "LIGHT_VEHICLE_RATE", "type": "Property"},
    {"object_id": "VOLUME_CLASSE_A", "name": "VOLUME_CLASSE_A", "type": "Property"},
    {"object_id": "VOLUME_CLASSE_B", "name": "VOLUME_CLASSE_B", "type": "Property"},
    {"object_id": "VOLUME_CLASSE_C", "name": "VOLUME_CLASSE_C", "type": "Property"},
    {"object_id": "VOLUME_CLASSE_D", "name": "VOLUME_CLASSE_D", "type": "Property"},
    {"object_id": "VOLUME_CLASSE_0", "name": "VOLUME_CLASSE_0", "type": "Property"},
    {"object_id": "axleClassVolumes", "name": "axleClassVolumes", "type": "Property"}
  ]
  ```

3. Step 3 — Publish MQTT message
  - Now you simulate the actual IoT sensor sending its readings. The IoT Agent handles wrapping these in the {"type": "Property", "value": ...} NGSI-LD structure, so your payload should just be the raw values.

  - API key: traffic-key

  - Device ID: traffic001

  - Payload: Copy and paste the following block:
  ```json
  {
    "dateObserved": "2015-01-01T11:55:00Z",
    "equipmentId": "121729",
    "laneDirection": "D",
    "intensity": 48,
    "averageVehicleSpeed": 97.77,
    "occupancy": 1.54,
    "AGG_ID": 448873,
    "AGG_PERIOD_LEN_MINS": 5,
    "NR_LANES": 3,
    "AVG_SPEED_HARMONIC": 94.9,
    "AVG_LENGTH": 443.75,
    "AVG_SPACING": 283.4,
    "LIGHT_VEHICLE_RATE": 100,
    "VOLUME_CLASSE_A": 0,
    "VOLUME_CLASSE_B": 48,
    "VOLUME_CLASSE_C": 0,
    "VOLUME_CLASSE_D": 0,
    "VOLUME_CLASSE_0": 0,
    "axleClassVolumes": { "E2": 48 }
  }
  ```

4. Step 4 — Query Orion-LD
  - Once the MQTT message is successfully published, the IoT agent will process it and update the context broker. You can verify the final NGSI-LD structure here.

  - Entity ID: urn:ngsi-ld:TrafficFlowObserved:9577808

  - Tenant: openiot (This matches the fiware-service header hardcoded in your Python script)