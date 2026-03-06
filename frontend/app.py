import streamlit as st
import pandas as pd
import os
import tempfile
import json
import jwt 
from streamlit_oauth import OAuth2Component

from backend.getDataMongoDB import get_sensor_data
from backend.getDataTimescaleDB import get_timescale_data
from backend.sendDataMongoDB import send_data_to_broker
from backend.sendDataTimescaleDB import send_notification_to_quantumleap

# --- Keycloak Configuration ---
AUTHORIZE_URL = "http://localhost:8080/realms/fiware-realm/protocol/openid-connect/auth"
TOKEN_URL = "http://keycloak:8080/realms/fiware-realm/protocol/openid-connect/token"
REVOKE_URL = "http://keycloak:8080/realms/fiware-realm/protocol/openid-connect/logout"

CLIENT_ID = "streamlit-app"
CLIENT_SECRET = ""

st.set_page_config(page_title="URBAN-NET Database", layout="wide")

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_file:
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
    
    # If Admin -> Show both tabs
    if is_admin:
        tabs = st.tabs(["📤 Send Data (Ingestion)", "📊 Get Data (Visualization)"])
        tab_ingestion = tabs[0]
        tab_visualization = tabs[1]
    # If Normal User -> Only create one tab
    else:
        tabs = st.tabs(["📊 Get Data (Visualization)"])
        tab_ingestion = None
        tab_visualization = tabs[0]

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

    # === TAB 2: GET DATA (Renders for everyone) ===
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
                        df = pd.DataFrame(history_data) if not isinstance(history_data, pd.DataFrame) else history_data
                        st.dataframe(df.head())
                        
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📊 Download CSV",
                            data=csv_data, file_name=f"historical_data_{entity_id}.csv", mime="text/csv"
                        )
                        
                        numeric_cols = df.select_dtypes(include=['float', 'int']).columns
                        if len(numeric_cols) > 0:
                            st.line_chart(df[numeric_cols])
                        else:
                            st.warning("No numeric data found to chart.")
                    else:
                        st.warning("No historical data found.")
                except Exception as e:
                    st.error(f"Could not fetch Timescale data: {e}")