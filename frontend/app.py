
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SmartCab",
    layout="wide"
)


#Session state

if "token" not in st.session_state:
    st.session_state.token = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "transport_refresh" not in st.session_state:
    st.session_state.transport_refresh = 0


#Authentication

def login(username, password):
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={
                "email": username,
                "password": password,
                "company_id": 1
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            st.session_state.token = data["access_token"]
            st.session_state.username = username

            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Hello! Welcome to SmartCab. "
                        "I'm your AI transport assistant. "
                        "How can I help you today?"
                    )
                }
            ]

            st.rerun()

        else:
            st.error("Invalid username or password.")

    except requests.RequestException:
        st.error("Unable to connect to the SmartCab server.")


def logout():
    st.session_state.token = None
    st.session_state.messages = []
    st.session_state.pop("username", None)
    st.rerun()


#CabLang API

def execute_cablang(command):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    try:
        response = requests.post(
            f"{API_URL}/cablang/execute",
            json={"command": command},
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            return response.json().get("result")

        return None

    except requests.RequestException:
        return None


#Chat API

def send_message(message):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    try:
        response = requests.post(
            f"{API_URL}/chat/message",
            json={"message": message},
            headers=headers,
            timeout=120
        )

        if response.status_code == 200:
            return response.json().get(
                "message",
                "I couldn't generate a response."
            )

        if response.status_code == 401:
            st.error("Your session has expired. Please log in again.")
            logout()

        else:
            try:
                detail = response.json().get("detail", "Unknown error")
            except ValueError:
                detail = response.text

            st.error(f"Chatbot error: {detail}")

    except requests.Timeout:
        st.error("The chatbot took too long to respond. Please try again.")

    except requests.RequestException:
        st.error("Unable to connect to the SmartCab server.")

    return None


#Login screen

if not st.session_state.token:

    st.title("SmartCab")
    st.caption("Intelligent AI Transportation")

    st.divider()

    _, center, _ = st.columns([1, 1.2, 1])

    with center:
        st.subheader("Welcome back")
        st.write("Sign in to access your SmartCab assistant.")

        username = st.text_input(
            "Username / Email",
            placeholder="employee@X.test"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login", use_container_width=True):
            if username and password:
                with st.spinner("Authenticating..."):
                    login(username, password)
            else:
                st.warning("Please enter your credentials.")


#Chat interface

else:

    #Retrieve transport information

    with st.spinner("Loading transport information..."):
        roster = execute_cablang("CHECK ROSTER")
        requests_data = execute_cablang("CHECK REQUESTS")

    #Sidebar

    with st.sidebar:

        st.title("SmartCab")
        st.caption("AI Transportation Assistant")

        st.divider()

        #Account information

        st.markdown("### Your Account")
        st.write(st.session_state.username)

        st.markdown(
            """
            <div style="
                background-color: #e8f5e9;
                color: #237a3b;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 13px;
                text-align: center;
                margin-bottom: 15px;
            ">
                Connected
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        #Current transport details

        st.markdown("### Current Transport")

        if isinstance(roster, list) and roster:
            current_slot = roster[0]

        elif isinstance(roster, dict) and roster:
            current_slot = roster

        else:
            current_slot = None

        if current_slot:

            st.metric(
                "Assigned Slot",
                current_slot.get("slot_id", "N/A")
            )

            st.metric(
                "Assigned Cab",
                current_slot.get("cab", "N/A")
            )

            st.metric(
                "Pickup Time",
                str(current_slot.get("time", "N/A"))
            )

            st.metric(
                "Service Date",
                str(current_slot.get("date", "N/A"))
            )

        else:
            st.info("No current transport assignment found.")

        st.divider()

        #Schedule changes

        st.markdown("### Schedule Changes")

        if isinstance(requests_data, list) and requests_data:
            i = 1
            for request_item in requests_data:

                with st.container(border=True):

                    st.markdown(
                        f"**Request #{i}**"
                    )
                    i+=1
                    st.write(
                        f"Slot: {request_item.get('requested_slot_id', 'N/A')}"
                    )

                    status = request_item.get("status", "UNKNOWN")

                    if status == "APPLIED":
                        st.success("APPLIED")

                    elif status == "WAITLISTED":
                        st.info("WAITLISTED — Waiting for an available seat")

                    elif status in ("PENDING", "APPROVAL_REQUIRED"):
                        st.warning(status)

                    elif status in ("REJECTED", "FAILED"):
                        st.error(status)

                    elif status == "SUPERSEDED":
                        st.caption("SUPERSEDED — Replaced by a newer request")

                    else:
                        st.info(status)

        elif isinstance(requests_data, dict) and requests_data:

            st.json(requests_data)

        elif requests_data is not None:

            st.info("No schedule change requests found.")

        else:

            st.warning("Unable to retrieve schedule changes.")

        st.divider()

        #Sidebar controls

        if st.button("Refresh Transport Details", use_container_width=True):
            st.rerun()

        if st.button("Logout", use_container_width=True):
            logout()


    #Main chat area

    st.title("AI Assistant")

    st.caption(
        "Ask questions about your transport schedule, "
        "available slots or request a shift change."
    )

    st.divider()

    #Suggested prompts

    if len(st.session_state.messages) == 1:

        st.markdown("#### What can I help you with?")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Show my current roster", use_container_width=True):
                st.session_state.pending_message = "Show my current roster."
                st.rerun()

            if st.button("Find available slots", use_container_width=True):
                st.session_state.pending_message = "Show me the available slots."
                st.rerun()

        with col2:
            if st.button("Check my requests", use_container_width=True):
                st.session_state.pending_message = "Show my shift change requests."
                st.rerun()

            if st.button("Show company transport policy", use_container_width=True):
                st.session_state.pending_message = "Show my company transport policy."
                st.rerun()


    #Display conversation

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    #Chat input

    user_input = st.chat_input("Message SmartCab...")

    if "pending_message" in st.session_state:
        user_input = st.session_state.pop("pending_message")


    #Process message

    if user_input:

        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):

            with st.spinner("SmartCab is thinking..."):
                assistant_response = send_message(user_input)

            if assistant_response:
                st.markdown(assistant_response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })

        st.rerun()
