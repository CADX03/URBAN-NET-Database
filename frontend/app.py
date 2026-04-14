import requests
import streamlit as st
import pandas as pd
import os
import tempfile
import json
import jwt 
import uuid
import io
import zipfile
from streamlit_oauth import OAuth2Component

from backend.getDataMongoDB import get_sensor_data
from backend.getDataTimescaleDB import get_timescale_data
from backend.sendDataMongoDB import send_data_to_broker
from backend.sendDataTimescaleDB import send_notification_to_quantumleap_in_batches
from backend.parserCSV import convert_csv_to_ngsild_stream
from backend.parserGTFS import process_gtfs_zip
from backend.parserGeoJSON import process_geojson_in_memory
from utils import save_uploaded_file, load_json_file, check_health_db
from backend.iot_agent_tester import (
    provision_service, delete_service, provision_device,
    delete_device, publish_mqtt, query_entity, check_health
)

# --- Keycloak Configuration ---
# Fetching from environment variables rather than hardcoding
AUTHORIZE_URL = os.getenv("KEYCLOAK_AUTHORIZE_URL")
TOKEN_URL = os.getenv("KEYCLOAK_TOKEN_URL")
REVOKE_URL = os.getenv("KEYCLOAK_REVOKE_URL")
BROWSER_LOGOUT_URL = os.getenv("KEYCLOAK_BROWSER_LOGOUT_URL")

CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
CLIENT_SECRET = ""

st.set_page_config(page_title="URBAN-NET Database", layout="wide")

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if "token" not in st.session_state:
    st.session_state["token"] = None

# ==========================================
# AUTHENTICATION ROUTING
# ==========================================

if st.session_state["token"] is None:
    st.title("🔒 Login Required")
    st.info("Please authenticate via Keycloak to access the URBAN-NET Database.")
    
    result = oauth2.authorize_button(
        name="Login with Keycloak",
        redirect_uri="http://localhost:8501",
        scope="openid profile email"
    )
    
    if result and "token" in result:
        st.session_state["token"] = result.get("token")
        st.rerun()

else:
    # --- Extract and Decode Token ---
    token_data = st.session_state["token"]
    access_token = token_data if isinstance(token_data, str) else token_data.get("access_token", "")
    
    is_admin = False
    decoded_token = {}
    try:
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        
        # 1. Check Realm roles (If you created the role at the Realm level)
        realm_roles = decoded_token.get("realm_access", {}).get("roles", [])
        
        # 2. Check Client roles (If you created the role specifically for the 'streamlit-app' client)
        client_roles = decoded_token.get("resource_access", {}).get(CLIENT_ID, {}).get("roles", [])
        
        # Grant admin access if "admin" is in EITHER list
        is_admin = "admin" in realm_roles or "admin" in client_roles
    except Exception as e:
        st.error(f"Failed to decode user token: {e}")

    # Sidebar for user info and logout
    with st.sidebar:
        st.success("Authenticated ✅")
        st.info(f"**Current Role:** {'Admin' if is_admin else 'Standard User'}") 
        
        if st.button("Logout"):
            id_token = token_data.get("id_token", "") if isinstance(token_data, dict) else ""
            st.session_state["token"] = None

            redirect_uri = "http://localhost:8501"
            keycloak_logout_url = f"{BROWSER_LOGOUT_URL}?post_logout_redirect_uri={redirect_uri}&id_token_hint={id_token}&client_id={CLIENT_ID}"
            
            st.markdown(f'<meta http-equiv="refresh" content="0;url={keycloak_logout_url}">', unsafe_allow_html=True)

    st.title("🎛️ URBAN-NET Database")

    # ==========================================
    # DYNAMIC TAB ROUTING
    # ==========================================
    
    # If Admin -> Show all tabs
    if is_admin:
        tabs = st.tabs([
            "📤 Send Data (Ingestion)", 
            "🚗 Convert CSV", 
            "🚇 Convert GTFS",
            "📍 Convert GeoJSON",
            "📊 Get Data (Visualization)",
            "🧪 IoT Agent Tester",
            "🏙️ Data Models"
        ])
        tab_ingestion = tabs[0]
        tab_conversion = tabs[1]
        tab_gtfs = tabs[2]
        tab_GeoJSON = tabs[3]
        tab_visualization = tabs[4]
        tab_iot_test = tabs[5]
        tab_models = tabs[6]
    # If Normal User -> Only show Visualization and Data Models
    else:
        tabs = st.tabs(["📊 Get Data (Visualization)", "🧪 IoT Agent Tester", "🏙️ Data Models"])
        tab_ingestion = None
        tab_conversion = None
        tab_gtfs = None
        tab_GeoJSON = None
        tab_visualization = tabs[0]
        tab_iot_test = tabs[1]
        tab_models = tabs[2]

    # === TAB 1: SEND DATA  ===
    if tab_ingestion is not None:
        with tab_ingestion:
            st.header("Data Ingestion")
            
            # --- Health Check ---
            with st.expander("Database health check", expanded=False):
                if st.button("Check services", key="db_health_check_button"):
                    health = check_health_db()
                    cols = st.columns(len(health))
                    for col, (name, status) in zip(cols, health.items()):
                        col.metric(name, status)

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("1. Update Context (Orion)")
                st.info("Upload a JSON file to update entities in Orion-LD.")
                uploaded_orion = st.file_uploader("Choose Orion JSON", type=['json'], key="orion_up")
                
                if st.button("Send to Orion"):
                    if uploaded_orion:
                        temp_path = save_uploaded_file(uploaded_orion)
                        try:
                            result = send_data_to_broker(temp_path) 
                            st.success(f"Success! Response: {result}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                        finally:
                            os.remove(temp_path)
                    else:
                        st.warning("Please upload a file first.")

            with col2:
                st.subheader("2. Configure Subscription (QuantumLeap)")
                st.info("Upload a JSON file to subscribe QuantumLeap to Orion changes.")
                uploaded_ql = st.file_uploader("Choose Subscription JSON", type=['json'], key="ql_up")
                
                if st.button("Send Notification/Sub"):
                    if uploaded_ql:
                        temp_path = save_uploaded_file(uploaded_ql)
                        try:
                            with st.spinner('Sending data in batches to QuantumLeap... Please wait.'):
                                result = send_notification_to_quantumleap_in_batches(temp_path)

                            st.success(f"Subscription Created! Response: {result}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                        finally:
                            os.remove(temp_path)
                    else:
                        st.warning("Please upload a file first.")

    # === TAB 2: CONVERT CSV ===
    if tab_conversion is not None:
        with tab_conversion:
            st.header("CSV to NGSI-LD Converter")
            st.info("Upload your raw CSV, choose the data model and attributes, and export to NGSI-LD.")
            
            data_models = ["TrafficFlowObserved", "WeatherObserved", "Generic"]
            selected_model = st.selectbox("Select Target NGSI-LD Data Model:", options=data_models)
            
            uploaded_csv = st.file_uploader("Choose CSV File", type=['csv'], key="csv_up")
            
            if uploaded_csv:
                uploaded_csv.seek(0)
                df = pd.read_csv(uploaded_csv, nrows=0)
                all_columns = df.columns.tolist()
                uploaded_csv.seek(0) 

                # 1. Define strictly required columns
                mandatory_columns = ["AGGREGATE_BY_LANE_BUNDLEID" ,"AGG_PERIOD_START", 
                                     "EQUIPMENTID", "LANE_BUNDLE_DIRECTION", "TOTAL_VOLUME", 
                                     "AVG_SPEED_ARITHMETIC", "OCCUPANCY"]

                # 2. Remove mandatory columns from the choices given to the user
                optional_columns = [col for col in all_columns if col not in mandatory_columns]

                st.info(f"The following columns are required and automatically included: {', '.join(mandatory_columns)}")

                user_selected_columns = st.multiselect(
                    "Select additional attributes to include in the NGSI-LD output:",
                    options=optional_columns,
                    default=optional_columns # Pre-selects the rest, or you can leave it empty: default=[]
                )

                # 3. Combine them in the background
                # (Only add mandatory columns if they actually existed in the original CSV)
                valid_mandatory_cols = [col for col in mandatory_columns if col in all_columns]

                final_selected_columns = valid_mandatory_cols + user_selected_columns
                
                if final_selected_columns:
                    # 1. Create a temp path for the input CSV
                    temp_csv_path = save_uploaded_file(uploaded_csv, suffix=".csv")
                    
                    # Create a temporary directory to hold all the JSON chunks
                    temp_dir = tempfile.mkdtemp()
                    
                    try:
                        with st.spinner("Converting large file and splitting into chunks... This might take a moment."):
                            # 2. Run the streaming converter with a 50,000 row limit per file
                            # (Adjust chunk_size if you want larger/smaller files)
                            row_count, json_files = convert_csv_to_ngsild_stream(
                                csv_file_path=temp_csv_path, 
                                output_dir=temp_dir, 
                                file_prefix=selected_model.lower(),
                                selected_columns=final_selected_columns, 
                                data_model=selected_model,
                                chunk_size=50000 
                            )
                        
                        st.success(f"✅ Ready! Successfully streamed {row_count} rows into {len(json_files)} files as `{selected_model}`.")
                        
                        # 3. Create a ZIP file in memory
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for json_file in json_files:
                                # Add each file to the zip without the full temporary path structure
                                zip_file.write(json_file, arcname=os.path.basename(json_file))
                        
                        # Reset the buffer's position to the beginning so it can be read by st.download_button
                        zip_buffer.seek(0)
                        
                        btn_col1, btn_col2 = st.columns([1, 1])
                        
                        # 4. Pass the ZIP buffer directly to the download button
                        st.download_button(
                                label="📥 Download ZIP Archive",
                                data=zip_buffer,
                                file_name=f"converted_{selected_model.lower()}_data.zip",
                                mime="application/zip",
                                use_container_width=True
                            )

                    except Exception as e:
                        st.error(f"Error processing CSV: {e}")
                    finally:
                        # Clean up the temporary CSV input file
                        if os.path.exists(temp_csv_path):
                            os.remove(temp_csv_path)
                            
                        # Clean up the temporary JSON chunks 
                        # (The ZIP exists in memory, so we can delete the files from disk immediately)
                        for f in os.listdir(temp_dir):
                            os.remove(os.path.join(temp_dir, f))
                        os.rmdir(temp_dir)
                        
                else:
                    st.warning("Please select at least one attribute to convert.")

    # === TAB 3: CONVERT GTFS ===
    if tab_gtfs is not None:
        with tab_gtfs:
            st.header("🚇 Dataset to NGSI-LD Converter (ZIP)")
            st.info("Upload your archive (ZIP), assign the appropriate Smart Data Model Contexts, and download the resulting NGSI-LD JSON files.")
            
            # Allow the user to inject a Smart Data Model Context
            available_domains = [
                "UrbanMobility", 
                "Transportation", 
                "Streetlighting",
                "Generic"
            ]
            
            selected_domain = st.selectbox(
                "Select a Data Model Context to apply:",
                options=available_domains,
                index=0 # Sets "UrbanMobility" as default since it's at index 0
            )

            uploaded_gtfs_zip = st.file_uploader("Choose ZIP Archive", type=['zip'], key="gtfs_zip_up")
            
            if uploaded_gtfs_zip:
                if not available_domains:
                    st.warning("⚠️ Please select at least one Data Model Context.")
                else:
                    if st.button("Convert to NGSI-LD"):
                        try:
                            with st.spinner("Extracting and processing files..."):
                                # Pass BOTH the file and the selected domains
                                converted_zip_buffer = process_gtfs_zip(
                                    uploaded_gtfs_zip, 
                                    selected_domain
                                )
                                
                            st.success("✅ Conversion successful! Your NGSI-LD entities are ready.")
                            
                            st.download_button(
                                label="📥 Download Converted Data (ZIP)",
                                data=converted_zip_buffer,
                                file_name="ngsi_ld_converted_data.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"An error occurred during conversion: {e}")

    # === TAB 4: CONVERT GeoJSON ===
    if tab_GeoJSON is not None:
        with tab_GeoJSON:
            st.header("📍 GeoJSON to NGSI-LD Converter")
            st.info("Upload a GeoJSON file, select the appropriate mapping, and convert it to NGSI-LD format. " \
            "Make sure to provide a valid Smart Data Model Context URL for proper semantic annotation. Look at the Smart Cities Data Models tab for examples of context URLs you can use.")

            col1, col2 = st.columns(2)
            available_options = {
                "OffStreetParking": "Parking", 
                "OnStreetParking": "Parking", 
                "ParkingAccess": "Parking"
            }

            options_list = list(available_options.items())

            # Entity Type Input
            selected_option = st.selectbox(
                "NGSI-LD Entity Type:",
                options=options_list,
                format_func=lambda option: f"{option[0]} (Category: {option[1]})",
                index=0
            )

            entity_type_input = selected_option[0]     # e.g., "OffStreetParking"
            entity_category_input = selected_option[1] # e.g., "Parking"
            
            # File uploader specific to GeoJSON/JSON
            uploaded_geojson = st.file_uploader("Choose GeoJSON File", type=['geojson', 'json'], key="geojson_up")

            if uploaded_geojson and entity_type_input and entity_category_input:
                if st.button("Convert to NGSI-LD", key="btn_convert_geojson"):
                    try:
                        with st.spinner("Processing GeoJSON..."):
                            # 1. Read the uploaded file into a Python dictionary
                            geojson_data = json.load(uploaded_geojson)
                            
                            # 2. Process the data using our helper function (passing the new context URL)
                            ngsild_data = process_geojson_in_memory(
                                geojson_data, 
                                entity_type_input, 
                                entity_category_input
                            )
                            
                            # 3. Convert the Python dictionary back to a formatted JSON string
                            converted_json_str = json.dumps(ngsild_data, indent=2, ensure_ascii=False)
                            
                        st.success("✅ Conversion successful! Your NGSI-LD entities are ready.")
                        
                        # 4. Provide the download button
                        st.download_button(
                            label="📥 Download Converted Data (JSON)",
                            data=converted_json_str,
                            file_name=f"{entity_type_input}_ngsild.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    except json.JSONDecodeError:
                        st.error("Error: The uploaded file is not a valid JSON document.")
                    except Exception as e:
                        st.error(f"An error occurred during conversion: {e}")
            
    # === TAB 5: GET DATA (Renders for everyone) ===
    with tab_visualization:
        st.header("Data Visualization")
        
        with st.container():
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                entity_id = st.text_input("Entity ID", value="")
            with c2:
                entity_type = st.text_input("Entity Type", value="")
            with c3:
                st.write("") 
                st.write("") 
                refresh = st.button("Fetch Data")

        tab_realtime, tab_history = st.tabs(["⏱️ Current State (MongoDB)", "📈 History (TimescaleDB)"])

        if refresh:
            # --- Real-time Data (Orion) ---
            with tab_realtime:
                try:
                    current_data = get_sensor_data(entity_id=entity_id, entity_type=entity_type)
                    json_str = json.dumps(current_data, indent=2)
                    
                    st.download_button(
                        label="📄 Download JSON",
                        data=json_str, file_name=f"current_data_{entity_id}.json", mime="application/json"
                    )
                    st.write("Or copy raw JSON:")
                    st.code(json_str, language="json")
                except Exception as e:
                    st.error(f"Could not fetch Orion data: {e}")

            # --- Historical Data (Timescale) ---
            with tab_history:
                try:
                    history_data = get_timescale_data(entity_id=entity_id, entity_type=entity_type)
                    if history_data:
                        
                        # --- 1. JSON DISPLAY & DOWNLOAD ---
                        st.subheader("Raw Data (JSON)")
                        json_str_history = json.dumps(history_data, indent=2)
                        
                        st.download_button(
                            label="📄 Download JSON",
                            data=json_str_history, 
                            file_name=f"historical_data_{entity_id}.json", 
                            mime="application/json"
                        )
                        
                        st.write("Or copy raw JSON:")
                        st.code(json_str_history, language="json")
                            
                        st.divider() # Adds a nice visual break

                    else:
                        st.warning("No historical data found.")
                
                except Exception as e:
                    st.error(f"Could not fetch Timescale data: {e}")
    
    # === TAB 6: IoT AGENT TESTER ===
    if tab_iot_test is not None:
        with tab_iot_test:
            st.header("IoT Agent Pipeline Tester")

            # --- Health Check ---
            with st.expander("Pipeline health check", expanded=False):
                if st.button("Check services"):
                    health = check_health()
                    cols = st.columns(len(health))
                    for col, (name, status) in zip(cols, health.items()):
                        col.metric(name, status)

            st.divider()

            # --- Step 1: Service Provisioning ---
            st.subheader("Step 1 — Provision service")
            col1, col2, col3, col4 = st.columns(4)
            svc_apikey   = col1.text_input("API key",       value="my-secret-key", key="svc_apikey")
            svc_type     = col2.text_input("Entity type",   value="Sensor",        key="svc_type")
            svc_resource = col3.text_input("Resource",      value="/iot/json",     key="svc_resource")
            svc_cbroker  = col4.text_input("Context broker",value="http://orion:1026", key="svc_cbroker")

            col_a, col_b = st.columns([1, 5])
            if col_a.button("Provision service"):
                code, body = provision_service(svc_apikey, svc_type, svc_resource, svc_cbroker)
                if code in (200, 201):
                    st.success(f"Service provisioned — {code}")
                else:
                    st.error(f"Failed ({code}): {body}")

            if col_b.button("Delete service"):
                code, body = delete_service(svc_apikey, svc_resource)
                st.info(f"Delete response ({code}): {body}")

            st.divider()

            # --- Step 2: Device Provisioning ---
            st.subheader("Step 2 — Provision device")
            col1, col2, col3, col4 = st.columns(4)
            dev_id      = col1.text_input("Device ID",    value="sensor001",             key="dev_id")
            dev_entity  = col2.text_input("Entity name",  value="urn:ngsi-ld:Sensor:001",key="dev_entity")
            dev_type    = col3.text_input("Entity type",  value="Sensor",                key="dev_type")
            dev_apikey  = col4.text_input("API key",      value="my-secret-key",         key="dev_apikey")

            st.markdown("**Attributes** — one per row: `object_id, name, type`")
            attrs_raw = st.text_area(
                "Attributes (JSON list)",
                value='[{"object_id": "t", "name": "temperature", "type": "Property"}]',
                height=100, key="dev_attrs"
            )

            col_a, col_b = st.columns([1, 5])
            if col_a.button("Provision device"):
                try:
                    attrs = json.loads(attrs_raw)
                    code, body = provision_device(dev_id, dev_entity, dev_type, dev_apikey, attrs)
                    if code in (200, 201):
                        st.success(f"Device provisioned — {code}")
                    else:
                        st.error(f"Failed ({code}): {body}")
                except json.JSONDecodeError:
                    st.error("Invalid JSON in attributes field.")

            if col_b.button("Delete device"):
                code, body = delete_device(dev_id)
                st.info(f"Delete response ({code}): {body}")

            st.divider()

            # --- Step 3: Publish MQTT ---
            st.subheader("Step 3 — Publish MQTT message")
            col1, col2, col3 = st.columns(3)
            mqtt_apikey  = col1.text_input("API key",   value="my-secret-key", key="mqtt_apikey")
            mqtt_dev     = col2.text_input("Device ID", value="sensor001",     key="mqtt_dev")
            mqtt_payload = col3.text_input("Payload",   value='{"t": 24.5}',  key="mqtt_payload")

            st.caption(f"Topic → `/{mqtt_apikey}/{mqtt_dev}/attrs`")

            if st.button("Publish"):
                try:
                    payload_dict = json.loads(mqtt_payload)
                    topic = publish_mqtt(mqtt_apikey, mqtt_dev, payload_dict)
                    st.success(f"Published to `{topic}`")
                except json.JSONDecodeError:
                    st.error("Payload must be valid JSON.")
                except Exception as e:
                    st.error(f"MQTT error: {e}")

            st.divider()

            # --- Step 4: Query Orion-LD ---
            st.subheader("Step 4 — Query Orion-LD")
            col1, col2 = st.columns([3, 1])
            query_id     = col1.text_input("Entity ID", value="urn:ngsi-ld:Sensor:001", key="q_id")
            query_tenant = col2.text_input("Tenant",    value="openiot",                key="q_tenant")

            if st.button("Query entity"):
                code, result = query_entity(query_id, query_tenant)
                if code == 200:
                    st.success(f"Entity found — {code}")
                    st.json(result)
                else:
                    st.error(f"Not found ({code}): {result}")

    # === TAB 7: SMART CITIES DATA MODELS ===
    with tab_models:
        st.header("🏙️ Smart Cities Data Models (NGSI-LD)")
        st.markdown("""
        This application utilizes harmonized **Smart Data Models** to ensure interoperability. 
        Below you can explore standard domain models typically used in Smart Cities.
        """)
        st.markdown("[View Full Specification for the Smart Cities Data Models 🔗](https://smartdatamodels.org/index.php/smart-cities-domain-at-smart-data-models/)")

        with st.expander("🚦 Traffic Flow Observed"):
            st.json(load_json_file('examples/traffic_flow.json'))
            st.markdown("[View Full Specification 🔗](https://github.com/smart-data-models/dataModel.Transportation/tree/master/TrafficFlowObserved)")

        with st.expander("🚌 Public Transport Stop GTFS (Urban Mobility)"):
            st.json(load_json_file('examples/gtfs_stop.json'))
            st.markdown("[View Full Specification 🔗](https://github.com/smart-data-models/dataModel.UrbanMobility/tree/master/GtfsStop)")
        
        with st.expander("🚗 Off-Street Parking (Parking)"):
            st.json(load_json_file('examples/off_street_parking.json'))
            st.markdown("[View Full Specification 🔗](https://github.com/smart-data-models/dataModel.Parking/tree/master/OffStreetParking)")