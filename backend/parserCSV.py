import os
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

def convert_csv_to_ngsild_stream(csv_file_path, output_dir, file_prefix, selected_columns, data_model, chunk_size=50000):
    """Reads CSV and streams NGSI-LD entities to multiple chunked JSON files."""
    
    generated_files = []
    
    with open(csv_file_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        chunk_index = 1
        count = 0
        row_count_in_chunk = 0
        outfile = None
        
        for index, row in enumerate(reader):
            # If we are starting a new chunk, open a new file
            if row_count_in_chunk == 0:
                current_file_path = os.path.join(output_dir, f"{file_prefix}_part{chunk_index}.json")
                generated_files.append(current_file_path)
                outfile = open(current_file_path, mode='w', encoding='utf-8')
                outfile.write("[\n")
            
            # Dispatch to the correct mapping function
            if data_model == "TrafficFlowObserved":
                entity = map_traffic_flow_observed(row, selected_columns, index)
            elif data_model == "WeatherObserved":
                entity = map_weather_observed(row, selected_columns, index)
            else:
                entity = map_generic_entity(row, selected_columns, data_model, index)
            
            # Add a comma before every entity EXCEPT the first one in the chunk
            if row_count_in_chunk > 0:
                outfile.write(",\n")
            
            # Dump the single entity directly into the file
            json.dump(entity, outfile, indent=2)
            
            count += 1
            row_count_in_chunk += 1
            
            # If we reached the chunk size limit, close the file and reset
            if row_count_in_chunk >= chunk_size:
                outfile.write("\n]")
                outfile.close()
                chunk_index += 1
                row_count_in_chunk = 0
                
        # Close the very last file if it wasn't closed by hitting the exact chunk limit
        if outfile and not outfile.closed:
            outfile.write("\n]")
            outfile.close()
            
    return count, generated_files


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
            entity["axleClassVolumes"] = {"type": "Property", "value": parse_axle_volumes(val)}
        elif col == "AGGREGATE_BY_LANE_BUNDLEID":
            pass # Handled in the entity ID
        else:
            entity[col] = {"type": "Property", "value": convert_to_number(val)}
            
    return entity

# The mapping function for WeatherObserved is similar in structure but tailored to its specific attributes and context. 
# It also includes a fallback mechanism for the entity ID, checking for both 'id' and 'ID' columns before defaulting to a generated ID based on the row index.
# Imcomplete!
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