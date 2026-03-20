import pandas as pd
import json
import zipfile
import io
import os
import tempfile

def format_gtfs_date(date_val):
    d_str = str(int(date_val))
    return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"

# --- Conversion Functions (Now accepting dynamic context) ---
def convert_agency(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsAgency:{row['agency_id']}",
        "type": "GtfsAgency",
        "agencyName": {"type": "Property", "value": row['agency_name']},
        "agencyUrl": {"type": "Property", "value": row['agency_url']},
        "agencyTimezone": {"type": "Property", "value": row['agency_timezone']},
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_stops(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsStop:Porto:{row['stop_id']}",
        "type": "GtfsStop",
        "name": {"type": "Property", "value": str(row['stop_name'])},
        "location": {
            "type": "GeoProperty",
            "value": {"type": "Point", "coordinates": [float(row['stop_lon']), float(row['stop_lat'])]}
        },
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_routes(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsRoute:Porto:{row['route_id']}",
        "type": "GtfsRoute",
        "shortName": {"type": "Property", "value": str(row['route_short_name'])},
        "routeType": {"type": "Property", "value": int(row['route_type'])},
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_trips(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsTrip:Porto:{row['trip_id']}",
        "type": "GtfsTrip",
        "hasRoute": {"type": "Relationship", "object": f"urn:ngsi-ld:GtfsRoute:Porto:{row['route_id']}"},
        "hasService": {"type": "Relationship", "object": f"urn:ngsi-ld:GtfsCalendarRule:Porto:{row['service_id']}"},
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_stop_times(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsStopTime:Porto:{row['trip_id']}_{row['stop_sequence']}",
        "type": "GtfsStopTime",
        "hasTrip": {"type": "Relationship", "object": f"urn:ngsi-ld:GtfsTrip:Porto:{row['trip_id']}"},
        "hasStop": {"type": "Relationship", "object": f"urn:ngsi-ld:GtfsStop:Porto:{row['stop_id']}"},
        "arrivalTime": {"type": "Property", "value": str(row['arrival_time'])},
        "departureTime": {"type": "Property", "value": str(row['departure_time'])},
        "stopSequence": {"type": "Property", "value": int(row['stop_sequence'])},
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_calendar(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsCalendarRule:Porto:{row['service_id']}",
        "type": "GtfsCalendarRule",
        "hasService": {"type": "Property", "value": str(row['service_id'])},
        "startDate": {"type": "Property", "value": format_gtfs_date(row['start_date'])},
        "endDate": {"type": "Property", "value": format_gtfs_date(row['end_date'])},
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_calendar_dates(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsCalendarDateRule:Porto:{row['service_id']}_{row['date']}",
        "type": "GtfsCalendarDateRule",
        "applicableDate": {"type": "Property", "value": format_gtfs_date(row['date'])},
        "exceptionType": {"type": "Property", "value": int(row['exception_type'])},
        "@context": context_list
    } for _, row in df.iterrows()]

def convert_shapes(df, context_list):
    entities = []
    for shape_id, group in df.groupby('shape_id'):
        sorted_group = group.sort_values('shape_pt_sequence')
        coordinates = [[float(row['shape_pt_lon']), float(row['shape_pt_lat'])] for _, row in sorted_group.iterrows()]
        
        entities.append({
            "id": f"urn:ngsi-ld:GtfsShape:Porto:{shape_id}",
            "type": "GtfsShape",
            "location": {"type": "GeoProperty", "value": {"type": "LineString", "coordinates": coordinates}},
            "@context": context_list
        })
    return entities

def convert_transfers(df, context_list):
    return [{
        "id": f"urn:ngsi-ld:GtfsTransferRule:Porto:{row['from_stop_id']}_{row['to_stop_id']}_{idx}",
        "type": "GtfsTransferRule",
        "transferType": {"type": "Property", "value": int(row['transfer_type'])},
        "@context": context_list
    } for idx, row in df.iterrows()]

# --- Main Orchestrator ---
def process_gtfs_zip(uploaded_zip_bytes, selected_domains):
    """
    Takes a ZIP file and a list of Smart Data Model domains.
    Generates the dynamic context and converts the data into chunked files.
    """
    # 1. Build the dynamic context based on user selection
    context_list = [
        f"https://raw.githubusercontent.com/smart-data-models/dataModel.{domain}/master/context.jsonld"
        for domain in selected_domains
    ]
    # Always include the core NGSI-LD context at the end
    context_list.append("https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld")

    out_zip_buffer = io.BytesIO()
    
    # Target ~80MB per JSON file. This is a balance between file size and number of files, but can be adjusted as needed.
    CHUNK_SIZE = 150000 
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(uploaded_zip_bytes, "r") as z:
            z.extractall(tmp_dir)
            
        extracted_files = os.listdir(tmp_dir)
        work_dir = tmp_dir
        if len(extracted_files) == 1 and os.path.isdir(os.path.join(tmp_dir, extracted_files[0])):
            work_dir = os.path.join(tmp_dir, extracted_files[0])

        file_map = {
            'agency.txt': ('agencies.json', convert_agency),
            'stops.txt': ('stops.json', convert_stops),
            'routes.txt': ('routes.json', convert_routes),
            'trips.txt': ('trips.json', convert_trips),
            'stop_times.txt': ('stop_times.json', convert_stop_times),
            'calendar.txt': ('calendar.json', convert_calendar),
            'calendar_dates.txt': ('calendar_dates.json', convert_calendar_dates),
            'shapes.txt': ('shapes.json', convert_shapes),
            'transfers.txt': ('transfers.json', convert_transfers)
        }

        with zipfile.ZipFile(out_zip_buffer, "w", zipfile.ZIP_DEFLATED) as out_zip:
            for txt_file, (json_filename, convert_func) in file_map.items():
                file_path = os.path.join(work_dir, txt_file)
                
                if os.path.exists(file_path):
                    base_name, ext = os.path.splitext(json_filename)
                    
                    # Read the CSV in chunks. This saves memory and allows easy file splitting.
                    # low_memory=False prevents mixed-type inference warnings on large files.
                    chunk_iter = pd.read_csv(file_path, chunksize=CHUNK_SIZE, low_memory=False)
                    
                    for i, df_chunk in enumerate(chunk_iter):
                        # Convert only the current chunk of data
                        entities = convert_func(df_chunk, context_list)
                        
                        # Determine filename: If it all fits in one chunk, use the original name.
                        # Otherwise, append _part1, _part2, etc.
                        if i == 0 and len(df_chunk) < CHUNK_SIZE:
                            out_filename = json_filename
                        else:
                            out_filename = f"{base_name}_part{i+1}{ext}"
                            
                        # Dump to string and write to the zip
                        json_str = json.dumps(entities, indent=2, ensure_ascii=False)
                        out_zip.writestr(out_filename, json_str)
                    
    out_zip_buffer.seek(0)
    return out_zip_buffer