import csv
import json
from datetime import datetime

def parse_axle_volumes(axle_str):
    axle_str = str(axle_str).strip('{}')
    if not axle_str or axle_str == 'nan':
        return {}
    volumes = {}
    for item in axle_str.split(';'):
        if ':' in item:
            key, val = item.split(':')
            volumes[key] = int(val)
    return volumes

def convert_to_number(val):
    try:
        if '.' in str(val):
            return float(val)
        return int(val)
    except ValueError:
        return val

def convert_csv_to_ngsild_stream(csv_file_path, output_json_path, selected_columns, data_model):
    """Reads CSV and streams NGSI-LD entities directly to a JSON file."""
    
    with open(csv_file_path, mode='r', encoding='utf-8') as infile, \
         open(output_json_path, mode='w', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        
        # Start the JSON array
        outfile.write("[\n")
        
        is_first = True
        count = 0
        
        for index, row in enumerate(reader):
            # Dispatch to the correct mapping function
            if data_model == "TrafficFlowObserved":
                entity = map_traffic_flow_observed(row, selected_columns, index)
            elif data_model == "WeatherObserved":
                entity = map_weather_observed(row, selected_columns, index)
            else:
                entity = map_generic_entity(row, selected_columns, data_model, index)
            
            # Add a comma before every entity EXCEPT the first one
            if not is_first:
                outfile.write(",\n")
            is_first = False
            
            # Dump the single entity directly into the file
            json.dump(entity, outfile, indent=2)
            count += 1
            
        # Close the JSON array
        outfile.write("\n]")
        
    return count 


def map_traffic_flow_observed(row, selected_columns, index):
    """Maps CSV rows specifically to the TrafficFlowObserved data model."""
    entity_id = row.get('AGGREGATE_BY_LANE_BUNDLEID', f"unknown_{index}")
    
    entity = {
        "id": f"urn:ngsi-ld:TrafficFlowObserved:{entity_id}",
        "type": "TrafficFlowObserved",
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
        ]
    }

    for col in selected_columns:
        val = row.get(col)
        if val is None or val == "":
            continue

        if col == "AGG_PERIOD_START":
            try:
                date_obj = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                iso_date = date_obj.isoformat() + "Z"
            except ValueError:
                iso_date = val 
            entity["dateObserved"] = {"type": "Property", "value": {"@type": "DateTime", "@value": iso_date}}
        elif col == "EQUIPMENTID":
            entity["equipmentId"] = {"type": "Property", "value": val}
        elif col == "LANE_BUNDLE_DIRECTION":
            entity["laneDirection"] = {"type": "Property", "value": val}
        elif col == "TOTAL_VOLUME":
            entity["intensity"] = {"type": "Property", "value": convert_to_number(val)}
        elif col == "AVG_SPEED_ARITHMETIC":
            entity["averageVehicleSpeed"] = {"type": "Property", "value": convert_to_number(val)}
        elif col == "OCCUPANCY":
            entity["occupancy"] = {"type": "Property", "value": convert_to_number(val)}
        elif col == "AXLE_CLASS_VOLUMES":
            # Assuming parse_axle_volumes is defined elsewhere in your code
            entity["axleClassVolumes"] = {"type": "Property", "value": parse_axle_volumes(val)}
        elif col == "AGGREGATE_BY_LANE_BUNDLEID":
            pass # Handled in the entity ID
        else:
            entity[col] = {"type": "Property", "value": convert_to_number(val)}
            
    return entity


def map_weather_observed(row, selected_columns, index):
    """Maps CSV rows specifically to the WeatherObserved data model."""
    # Fallback to 'id', 'ID', or the row index
    entity_id = row.get('id', row.get('ID', f"station_{index}"))
    
    entity = {
        "id": f"urn:ngsi-ld:WeatherObserved:{entity_id}",
        "type": "WeatherObserved",
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "https://raw.githubusercontent.com/smart-data-models/dataModel.Weather/master/context.jsonld"
        ]
    }

    for col in selected_columns:
        val = row.get(col)
        if val is None or val == "":
            continue

        if col == "TEMP":
            entity["temperature"] = {"type": "Property", "value": convert_to_number(val)}
        else:
            entity[col] = {"type": "Property", "value": convert_to_number(val)}
            
    return entity


def map_generic_entity(row, selected_columns, data_model, index):
    """A fallback mapper for any models that don't have explicit rules yet."""
    entity_id = row.get('id', row.get('ID', f"entity_{index}"))
    
    entity = {
        "id": f"urn:ngsi-ld:{data_model}:{entity_id}",
        "type": data_model,
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    }

    for col in selected_columns:
        val = row.get(col)
        if val is None or val == "":
            continue
            
        # Generically map everything as a standard NGSI-LD Property
        entity[col] = {"type": "Property", "value": convert_to_number(val)}
        
    return entity