import streamlit as st
import pandas as pd
import os
import tempfile
import json
import jwt 
import uuid
from streamlit_oauth import OAuth2Component

from backend.getDataMongoDB import get_sensor_data
from backend.getDataTimescaleDB import get_timescale_data
from backend.sendDataMongoDB import send_data_to_broker
from backend.sendDataTimescaleDB import send_notification_to_quantumleap
from backend.parserCSV import convert_csv_to_ngsild_stream

# --- Keycloak Configuration ---
AUTHORIZE_URL = "http://localhost:8080/realms/fiware-realm/protocol/openid-connect/auth"
TOKEN_URL = "http://keycloak:8080/realms/fiware-realm/protocol/openid-connect/token"
REVOKE_URL = "http://keycloak:8080/realms/fiware-realm/protocol/openid-connect/logout"

CLIENT_ID = "streamlit-app"
CLIENT_SECRET = ""

st.set_page_config(page_title="URBAN-NET Database", layout="wide")

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

def save_uploaded_file(uploaded_file, suffix=".json"):
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    return None

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
            st.session_state["token"] = None
            st.rerun()

    st.title("🎛️ URBAN-NET Database")

    # ==========================================
    # DYNAMIC TAB ROUTING
    # ==========================================
    
    # If Admin -> Show all tabs
    if is_admin:
        tabs = st.tabs([
            "📤 Send Data (Ingestion)", 
            "🔄 Convert CSV", 
            "📊 Get Data (Visualization)", 
            "🏙️ Data Models"
        ])
        tab_ingestion = tabs[0]
        tab_conversion = tabs[1]
        tab_visualization = tabs[2]
        tab_models = tabs[3]
    # If Normal User -> Only show Visualization and Data Models
    else:
        tabs = st.tabs(["📊 Get Data (Visualization)", "🏙️ Data Models"])
        tab_ingestion = None
        tab_conversion = None
        tab_visualization = tabs[0]
        tab_models = tabs[1]

    # === TAB 1: SEND DATA (Only renders if tab_ingestion exists) ===
    if tab_ingestion is not None:
        with tab_ingestion:
            st.header("Data Ingestion")
            
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
                            result = send_notification_to_quantumleap(temp_path)
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
            
            data_models = ["TrafficFlowObserved", "WeatherObserved", "Device", "Generic"]
            selected_model = st.selectbox("Select Target NGSI-LD Data Model:", options=data_models)
            
            uploaded_csv = st.file_uploader("Choose CSV File", type=['csv'], key="csv_up")
            
            if uploaded_csv:
                uploaded_csv.seek(0)
                df = pd.read_csv(uploaded_csv, nrows=0)
                all_columns = df.columns.tolist()
                uploaded_csv.seek(0) 
                
                selected_columns = st.multiselect(
                    "Select attributes to include in the NGSI-LD output:",
                    options=all_columns,
                    default=all_columns 
                )
                
                if selected_columns:
                    # 1. Create temporary paths for BOTH input and output
                    temp_csv_path = save_uploaded_file(uploaded_csv, suffix=".csv")
                    
                    # Create a persistent temp file for the JSON output
                    fd, temp_json_path = tempfile.mkstemp(suffix=".json")
                    os.close(fd) # Close the file descriptor so our function can open it
                    
                    try:
                        with st.spinner("Converting large file... This might take a moment."):
                            # 2. Run the streaming converter
                            row_count = convert_csv_to_ngsild_stream(
                                temp_csv_path, 
                                temp_json_path, 
                                selected_columns, 
                                selected_model
                            )
                        
                        st.success(f"✅ Ready! Successfully streamed {row_count} rows as `{selected_model}`.")
                        
                        btn_col1, btn_col2 = st.columns([1, 1])
                        
                        # 3. Pass the file directly to the download button
                        with btn_col1:
                            with open(temp_json_path, "rb") as file:
                                st.download_button(
                                    label="📥 Download JSON",
                                    data=file,
                                    file_name=f"converted_{selected_model.lower()}_data.json",
                                    mime="application/json",
                                    use_container_width=True
                                )

                        # with btn_col2:
                        #     if st.button("🚀 Send to Orion", use_container_width=True):
                        #         with st.spinner("Sending to broker..."):
                        #             try:
                        #                 # Your existing broker function already takes a file path!
                        #                 result = send_data_to_broker(temp_json_path)
                        #                 st.success(f"Data sent to Orion! Response: {result}")
                        #             except Exception as e:
                        #                 st.error(f"Error sending to broker: {e}")
        
                    except Exception as e:
                        st.error(f"Error processing CSV: {e}")
                    finally:
                        # Clean up temporary files
                        if os.path.exists(temp_csv_path):
                            os.remove(temp_csv_path)
                        # Note: We don't delete temp_json_path immediately if the user might click Download again.
                        # Streamlit reruns the script on button clicks, so standard temp files can be tricky.
                        # Using mkstemp keeps it alive until the app restarts or we manually clean it up.
                else:
                    st.warning("Please select at least one attribute to convert.")
                
    # === TAB 3: GET DATA (Renders for everyone) ===
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
    
    # === TAB 4: SMART CITIES DATA MODELS ===
    with tab_models:
        st.header("🏙️ Smart Cities Data Models (NGSI-LD)")
        st.markdown("""
        This application utilizes harmonized **Smart Data Models** to ensure interoperability. 
        Below you can explore standard domain models typically used in Smart Cities.
        """)

        # Option A: Interactive Expanders with common examples
        with st.expander("🚦 Traffic Flow Observed"):
            st.json({
                "id": "urn:ngsi-ld:TrafficFlowObserved:1",
                "type": "TrafficFlowObserved",
                "dateObserved": {"type": "Property", "value": "2023-10-25T12:00:00Z"},
                "intensity": {"type": "Property", "value": 450},
                "averageVehicleSpeed": {"type": "Property", "value": 52},
                "location": {
                    "type": "GeoProperty",
                    "value": {
                        "type": "Point",
                        "coordinates": [-8.5, 41.2]
                    }
                }
            })
            st.markdown("[View Full Specification 🔗](https://github.com/smart-data-models/dataModel.Transportation/tree/master/TrafficFlowObserved)")

        with st.expander("💡 Streetlight"):
            st.json({
                "id": "urn:ngsi-ld:Streetlight:1",
                "type": "Streetlight",
                "powerState": {"type": "Property", "value": "on"},
                "illuminanceLevel": {"type": "Property", "value": 0.8},
                "location": {
                    "type": "GeoProperty",
                    "value": {
                        "type": "Point",
                        "coordinates": [-8.6, 41.1]
                    }
                }
            })
            st.markdown("[View Full Specification 🔗](https://github.com/smart-data-models/dataModel.Streetlighting)")