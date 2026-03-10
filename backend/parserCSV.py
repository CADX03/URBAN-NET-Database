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

def csv_to_ngsild(input_csv, output_json):
    ngsi_ld_entities = []

    with open(input_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # 1. Format the date to ISO 8601
            raw_date = row["AGG_PERIOD_START"]
            try:
                date_obj = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                iso_date = date_obj.isoformat() + "Z"
            except ValueError:
                iso_date = raw_date # Fallback if format is unexpected

            # 2. Build the base NGSI-LD Entity
            entity = {
                "id": f"urn:ngsi-ld:TrafficFlowObserved:{row['AGGREGATE_BY_LANE_BUNDLEID']}",
                "type": "TrafficFlowObserved",
                "@context": [
                    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
                    "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
                ],
                
                # Standardized TrafficFlowObserved properties
                "dateObserved": {
                    "type": "Property",
                    "value": {
                        "@type": "DateTime",
                        "@value": iso_date
                    }
                },
                "equipmentId": {
                    "type": "Property",
                    "value": row["EQUIPMENTID"]
                },
                "laneDirection": {
                    "type": "Property",
                    "value": row["LANE_BUNDLE_DIRECTION"]
                },
                "intensity": {
                    "type": "Property",
                    "value": convert_to_number(row["TOTAL_VOLUME"])
                },
                "averageVehicleSpeed": {
                    "type": "Property",
                    "value": convert_to_number(row["AVG_SPEED_ARITHMETIC"])
                },
                "occupancy": {
                    "type": "Property",
                    "value": convert_to_number(row["OCCUPANCY"])
                }
            }

            # 3. Add the rest of the attributes dynamically
            skip_keys = {"AGGREGATE_BY_LANE_BUNDLEID", "AGG_PERIOD_START", "EQUIPMENTID", 
                         "LANE_BUNDLE_DIRECTION", "TOTAL_VOLUME", "AVG_SPEED_ARITHMETIC", 
                         "OCCUPANCY", "AXLE_CLASS_VOLUMES"}
            
            for key, value in row.items():
                if key not in skip_keys:
                    entity[key] = {
                        "type": "Property",
                        "value": convert_to_number(value)
                    }

            # Handle the custom AXLE_CLASS_VOLUMES string
            entity["axleClassVolumes"] = {
                "type": "Property",
                "value": parse_axle_volumes(row["AXLE_CLASS_VOLUMES"])
            }

            ngsi_ld_entities.append(entity)

    # 4. Write to JSON file
    with open(output_json, mode='w', encoding='utf-8') as outfile:
        json.dump(ngsi_ld_entities, outfile, indent=2)
        
    print(f"Successfully converted {len(ngsi_ld_entities)} records to NGSI-LD format in '{output_json}'.")

def convert_csv_to_ngsild(csv_file_path):
    ngsi_ld_entities = []
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            raw_date = row.get("AGG_PERIOD_START", "")
            try:
                date_obj = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                iso_date = date_obj.isoformat() + "Z"
            except ValueError:
                iso_date = raw_date 

            entity = {
                "id": f"urn:ngsi-ld:TrafficFlowObserved:{row.get('AGGREGATE_BY_LANE_BUNDLEID', 'unknown')}",
                "type": "TrafficFlowObserved",
                "@context": [
                    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
                    "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
                ],
                "dateObserved": {"type": "Property", "value": {"@type": "DateTime", "@value": iso_date}},
                "equipmentId": {"type": "Property", "value": row.get("EQUIPMENTID")},
                "laneDirection": {"type": "Property", "value": row.get("LANE_BUNDLE_DIRECTION")},
                "intensity": {"type": "Property", "value": convert_to_number(row.get("TOTAL_VOLUME"))},
                "averageVehicleSpeed": {"type": "Property", "value": convert_to_number(row.get("AVG_SPEED_ARITHMETIC"))},
                "occupancy": {"type": "Property", "value": convert_to_number(row.get("OCCUPANCY"))},
                "axleClassVolumes": {"type": "Property", "value": parse_axle_volumes(row.get("AXLE_CLASS_VOLUMES", ""))}
            }

            skip_keys = {"AGGREGATE_BY_LANE_BUNDLEID", "AGG_PERIOD_START", "EQUIPMENTID", 
                         "LANE_BUNDLE_DIRECTION", "TOTAL_VOLUME", "AVG_SPEED_ARITHMETIC", 
                         "OCCUPANCY", "AXLE_CLASS_VOLUMES"}
            
            for key, value in row.items():
                if key not in skip_keys and value is not None:
                    entity[key] = {"type": "Property", "value": convert_to_number(value)}

            ngsi_ld_entities.append(entity)
    return ngsi_ld_entities

# Run the function
if __name__ == "__main__":
    csv_to_ngsild('./../dataCSV/test.csv', './../output/traffic_data_ngsild.json')