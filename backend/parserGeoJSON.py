import json
import uuid

def create_ngsild_entity(feature, entity_type):
    """Converts a single GeoJSON feature dictionary into an NGSI-LD entity dictionary."""
    
    raw_id = feature.get("id")
    if not raw_id:
        raw_id = str(uuid.uuid4())
    entity_id = f"urn:ngsi-ld:{entity_type}:{raw_id}"

    ngsild_entity = {
        "id": entity_id,
        "type": entity_type
    }

    geometry = feature.get("geometry")
    if geometry:
        ngsild_entity["location"] = {
            "type": "GeoProperty",
            "value": geometry
        }

    properties = feature.get("properties", {})
    for key, value in properties.items():
        if value is None or value == "":
            continue
            
        safe_key = key.replace(" ", "_")
        if safe_key == "id":
            safe_key = "original_id"
        elif safe_key == "type":
            safe_key = "original_type"

        ngsild_entity[safe_key] = {
            "type": "Property",
            "value": value
        }

    return ngsild_entity

def process_geojson_in_memory(geojson_data, entity_type, domain_context_url):
    """Processes a parsed GeoJSON dictionary and returns a list of NGSI-LD dictionaries."""
    
    features = []
    if geojson_data.get("type") == "FeatureCollection":
        features = geojson_data.get("features", [])
    elif geojson_data.get("type") == "Feature":
        features = [geojson_data]
    else:
        raise ValueError("Invalid GeoJSON format. Root object must be a FeatureCollection or Feature.")

    ngsild_entities = [create_ngsild_entity(feat, entity_type) for feat in features]

    core_context_url = "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
    
    # Apply the context array exactly as requested
    for entity in ngsild_entities:
        entity["@context"] = [
            domain_context_url,
            core_context_url
        ]
    return ngsild_entities