import os
import requests
import json
import paho.mqtt.publish as publish

IOTA_URL  = f"http://{os.getenv('IOTA_HOST', 'iot-agent')}:4041"
ORION_URL = f"http://{os.getenv('ORION_HOST', 'orion')}:1026"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

def provision_service(apikey, entity_type, resource, cbroker):
    r = requests.post(
        f"{IOTA_URL}/iot/services",
        headers={"Content-Type": "application/json",
                 "fiware-service": "openiot", "fiware-servicepath": "/"},
        json={"services": [{"apikey": apikey, "cbroker": cbroker,
                             "entity_type": entity_type, "resource": resource}]}
    )
    return r.status_code, r.text

def delete_service(apikey, resource):
    r = requests.delete(
        f"{IOTA_URL}/iot/services/",
        headers={"fiware-service": "openiot", "fiware-servicepath": "/"},
        params={"resource": resource, "apikey": apikey}
    )
    return r.status_code, r.text

def provision_device(device_id, entity_name, entity_type, apikey, attributes):
    r = requests.post(
        f"{IOTA_URL}/iot/devices",
        headers={"Content-Type": "application/json",
                 "fiware-service": "openiot", "fiware-servicepath": "/"},
        json={"devices": [{
            "device_id": device_id, "entity_name": entity_name,
            "entity_type": entity_type, "protocol": "IoTA-JSON",
            "transport": "MQTT", "apikey": apikey,
            "attributes": attributes
        }]}
    )
    return r.status_code, r.text

def delete_device(device_id):
    r = requests.delete(
        f"{IOTA_URL}/iot/devices/{device_id}",
        headers={"fiware-service": "openiot", "fiware-servicepath": "/"}
    )
    return r.status_code, r.text

def publish_mqtt(apikey, device_id, payload: dict):
    topic = f"/{apikey}/{device_id}/attrs"
    publish.single(topic, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)
    return topic

def query_entity(entity_id, tenant="openiot"):
    r = requests.get(
        f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}",
        headers={"NGSILD-Tenant": tenant, "Accept": "application/ld+json"}
    )
    return r.status_code, r.json() if r.ok else r.text

def check_health():
    results = {}
    for name, url in [("IoT Agent", f"{IOTA_URL}/iot/about"),
                      ("Orion-LD", f"{ORION_URL}/ngsi-ld/v1/types")]:
        try:
            r = requests.get(url, timeout=3)
            results[name] = "🟢 Reachable" if r.ok else f"🔴 {r.status_code}"
        except Exception:
            results[name] = "🔴 Unreachable"
    return results