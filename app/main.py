import sys
import os
from datetime import time, timedelta, datetime, date
import streamlit as st
from app.database import init_db, session, User, Vacation, Settings
from app.user_auth import login_user, register_user

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set page configuration (must be the first Streamlit command)
st.set_page_config(page_title="Vacation Manager", layout="wide")

# Initialize session state variables if they don't exist
if 'vacation_start_date' not in st.session_state:
    st.session_state.vacation_start_date = None
if 'vacation_end_date' not in st.session_state:
    st.session_state.vacation_end_date = None
if 'vacation_start_time' not in st.session_state:
    st.session_state.vacation_start_time = time(7, 30)
if 'vacation_end_time' not in st.session_state:
    st.session_state.vacation_end_time = time(16, 0)

# Custom CSS for background, sidebar, text colors, and selectbox
st.markdown(
    """
    <style>
    /* Set the background color for the entire app */
    .main {
        background-color: #0e57b3;
    }
    /* Set the background color for the sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0c3f80 !important;
    }
    /* Set the background color and text color for the selectbox */
    .css-16huue1, .css-11ifdcj {
        background-color: #0c3f80 !important;
        color: #ffffff !important;
    }
    /* Set the color for text globally */
    .css-10trblm, .css-1kyxreq, .css-1cpxqw2, .css-qbe2hs, .css-1d391kg, .css-1v0mbdj, .css-1d391kg, .css-1cpxqw2, .css-10trblm, .css-2trqyj, .stMarkdown {
        color: #ffffff !important;
    }
    /* Ensure all headers and titles are white */
    h1, h2, h3, h4, h5, h6, .css-1cpxqw2, .css-10trblm, .stText, .stMarkdown, .stCaption, .stExpanderHeader, .st-expander-label {
        color: #ffffff !important;
    }
    /* Ensure labels in forms and selectors are white */
    .stNumberInput > label, .stSelectbox > label, .stTextInput > label, .stDateInput > label, .stTimeInput > label {
        color: #ffffff !important;
    }
    /* Custom styles for calendar buttons */
    .calendar-button {
        width: 100%;
        height: 40px;
        font-size: small;
        text-align: center;
        border-radius: 5px;
        color: black;
        margin: 0;
        padding: 0;
        border: none;
    }
    .calendar-button.approved {
        background-color: green;
    }
    .calendar-button.pending {
        background-color: orange;
    }
    .calendar-button.denied {
        background-color: red;
    }
    .calendar-button.selected {
        background-color: darkblue;
    }
    .calendar-button.default {
        background-color: white;
    }
    /* Set the color of the expander header text to white */
    .streamlit-expanderHeader, .streamlit-expanderHeader > label {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to format the date
def format_date(d):
    return d.strftime('%d-%m-%Y')

# Function to format the time
def format_time(t):
    return t.strftime('%H:%M') if t else "Full Day"

# Function to delete a specific vacation
def delete_vacation(vacation_id):
    session.query(Vacation).filter(Vacation.id == vacation_id).delete()
    session.commit()

# Function to check vacation limits
def check_vacation_limits(user_role, start_date, end_date):
    settings = session.query(Settings).first()
    if user_role == 'Dreher':
        limit = settings.dreher_limit
    elif user_role == 'Fräser':
        limit = settings.fraeser_limit
    elif user_role == 'Schweißer':
        limit = settings.schweisser_limit
    else:
        return True  # No limit for other roles

    overlapping_vacations = session.query(Vacation).join(User).filter(
        User.role == user_role,
        Vacation.status == 'approved',
        Vacation.start_date <= end_date,
        Vacation.end_date >= start_date
    ).count()

    return overlapping_vacations < limit

# Function to calculate used vacation days
def calculate_used_vacation_days(user_id):
    approved_vacations = session.query(Vacation).filter_by(user_id=user_id, status='approved').all()
    used_days = sum(calculate_vacation_days(vacation.start_date, vacation.end_date, vacation.start_time, vacation.end_time) for vacation in approved_vacations)
    return used_days

# Function to calculate remaining vacation days
def calculate_remaining_vacation_days(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    used_days = calculate_used_vacation_days(user_id)
    return user.vacation_days - used_days

# Function to calculate the exact number of vacation days based on times
def calculate_vacation_days(start_date, end_date, start_time, end_time):
    full_days = (end_date - start_date).days
    total_days = 0.0

    if full_days > 0:
        first_day_hours = (datetime.combine(date.today(), time(16, 0)) - datetime.combine(date.today(), start_time)).seconds / 3600.0
        if start_time <= time(12, 0) and end_time > time(12, 30):
            first_day_hours -= 0.5  # Deduct lunch break if it falls within the vacation period
        total_days += first_day_hours / 8.0

        total_days += full_days - 1

        last_day_hours = (datetime.combine(date.today(), end_time) - datetime.combine(date.today(), time(7, 30))).seconds / 3600.0
        if start_time <= time(12, 0) and end_time > time(12, 30):
            last_day_hours -= 0.5  # Deduct lunch break if it falls within the vacation period
        total_days += last_day_hours / 8.0
    else:
        work_hours = (datetime.combine(date.today(), end_time) - datetime.combine(date.today(), start_time)).seconds / 3600.0
        if start_time <= time(12, 0) and end_time > time(12, 30):
            work_hours -= 0.5  # Deduct lunch break if it falls within the vacation period
        total_days += work_hours / 8.0

    return round(total_days, 4)

# Valid times for selection
valid_times = [time(7, 30), time(8, 0), time(8, 30), time(9, 0), time(9, 30), time(10, 0), 
               time(10, 30), time(11, 0), time(11, 30), time(12, 0), time(12, 30), time(13, 0), 
               time(13, 30), time(14, 0), time(14, 30), time(15, 0), time(15, 30), time(16, 0)]

# Initialize the database
init_db()

# Ensure that settings are initialized
def initialize_settings():
    settings = session.query(Settings).first()
    if not settings:
        settings = Settings(dreher_limit=2, fraeser_limit=2, schweisser_limit=2)
        session.add(settings)
        session.commit()

initialize_settings()

# Insert company logo
st.image("https://raw.githubusercontent.com/TomGroeber/Urlaub-nehmen/main/assets/logo.png", width=300)

st.title("Vacation Manager")

# Login
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.subheader("Login to Your Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    if user.role == 'Admin':
        st.write(f"Welcome, {user.username}!")
        st.write(f"Role: {user.role}")
        st.write("You have ∞ vacation days remaining.")
    else:
        remaining_days = calculate_remaining_vacation_days(user.id)
        st.write(f"Welcome, {user.username}!")
        st.write(f"Role: {user.role}")
        st.write(f"You have {remaining_days:.4f} vacation days remaining.")

    # Admin view
    if user.role == 'Admin':
        admin_choice = st.sidebar.selectbox("Admin Actions", ["Manage Vacation Requests", "Manage Users", "Set Limits", "Create User"])
        
        if admin_choice == "Manage Vacation Requests":
            st.subheader("Admin View: Vacation Requests")

            pending_vacations = session.query(Vacation).filter_by(status='pending').all()
            processed_vacations = session.query(Vacation).filter(Vacation.status != 'pending').all()

            # Display pending requests
            if pending_vacations:
                st.markdown("### Pending Requests")
                for vacation in pending_vacations:
                    requester = session.query(User).filter_by(id=vacation.user_id).first()
                    st.markdown(f"<div style='font-weight: bold;'>{requester.username} ({requester.role}): <br>{format_date(vacation.start_date)} to {format_date(vacation.end_date)} <br><span style='color: orange;'>{vacation.status}</span></div>", unsafe_allow_html=True)
                    st.write(f"**Note:** {vacation.note}")
                    st.write(f"**Time:** {format_time(vacation.start_time)} - {format_time(vacation.end_time)}")
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        if st.button(f"Approve {vacation.id}", key=f"approve_{vacation.id}"):
                            if not check_vacation_limits(requester.role, vacation.start_date, vacation.end_date):
                                st.warning(f"Cannot approve vacation for {requester.username}. Limit for {requester.role} reached.")
                            else:
                                vacation.status = 'approved'
                                session.commit()
                                st.experimental_rerun()
                        if st.button(f"Deny {vacation.id}", key=f"deny_{vacation.id}"):
                            vacation.status = 'denied'
                            session.commit()
                            st.experimental_rerun()
                    with col2:
                        new_start_date = st.date_input("Start Date", vacation.start_date, key=f"start_{vacation.id}")
                        new_end_date = st.date_input("End Date", vacation.end_date, key=f"end_{vacation.id}")
                        start_time = vacation.start_time if vacation.start_time else valid_times[0]
                        end_time = vacation.end_time if vacation.end_time else valid_times[-1]
                        new_start_time = st.selectbox("Start Time", valid_times, index=valid_times.index(start_time), key=f"start_time_{vacation.id}")
                        new_end_time = st.selectbox("End Time", valid_times, index=valid_times.index(end_time), key=f"end_time_{vacation.id}")
                        if st.button(f"Update {vacation.id}", key=f"update_{vacation.id}"):
                            vacation.start_date = new_start_date
                            vacation.end_date = new_end_date
                            vacation.start_time = new_start_time
                            vacation.end_time = new_end_time
                            session.commit()
                            st.experimental_rerun()
                    with col3:
                        if st.button(f"Delete {vacation.id}", key=f"delete_{vacation.id}"):
                            delete_vacation(vacation.id)
                            session.commit()
                            st.experimental_rerun()
                    st.markdown("<hr>", unsafe_allow_html=True)  # Separation between requests

            # Display processed requests
            if processed_vacations:
                with st.expander("Processed Requests", expanded=False):
                    for vacation in processed_vacations:
                        requester = session.query(User).filter_by(id=vacation.user_id).first()
                        st.markdown(f"<div style='font-weight: bold;'>{requester.username} ({requester.role}): <br>{format_date(vacation.start_date)} to {format_date(vacation.end_date)} <br><span style='color: green;'>{vacation.status}</span></div>", unsafe_allow_html=True)
                        st.write(f"**Note:** {vacation.note}")
                        st.write(f"**Time:** {format_time(vacation.start_time)} - {format_time(vacation.end_time)}")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            new_start_date = st.date_input("Start Date", vacation.start_date, key=f"start_{vacation.id}")
                            new_end_date = st.date_input("End Date", vacation.end_date, key=f"end_{vacation.id}")
                            start_time = vacation.start_time if vacation.start_time else valid_times[0]
                            end_time = vacation.end_time if vacation.end_time else valid_times[-1]
                            new_start_time = st.selectbox("Start Time", valid_times, index=valid_times.index(start_time), key=f"start_time_{vacation.id}")
                            new_end_time = st.selectbox("End Time", valid_times, index=valid_times.index(end_time), key=f"end_time_{vacation.id}")
                            if st.button(f"Update {vacation.id}", key=f"update_{vacation.id}"):
                                vacation.start_date = new_start_date
                                vacation.end_date = new_end_date
                                vacation.start_time = new_start_time
                                vacation.end_time = new_end_time
                                session.commit()
                                st.experimental_rerun()
                        with col2:
                            if st.button(f"Delete {vacation.id}", key=f"delete_{vacation.id}"):
                                delete_vacation(vacation.id)
                                session.commit()
                                st.experimental_rerun()
                        st.markdown("<hr>", unsafe_allow_html=True)  # Separation between requests

            # Button to reset all vacations
            st.markdown("---")
            if st.button("Reset All Vacations"):
                session.query(Vacation).delete()
                session.commit()
                st.experimental_rerun()
                st.success("All vacation entries have been reset.")
        
        if admin_choice == "Manage Users":
            st.subheader("Admin View: Manage Users")
            users = session.query(User).all()
            
            for user in users:
                if user.username != 'admin':
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                    with col1:
                        st.write(f"**{user.username} ({user.role})**")
                    with col2:
                        remaining_days = calculate_remaining_vacation_days(user.id)
                        new_vacation_days = st.number_input(f"Set Vacation Days for {user.username}", min_value=0.0, value=float(remaining_days), step=0.1, format="%.4f", key=f"vac_days_{user.id}")
                        new_monthly_days = st.number_input(f"Monthly Vacation Days for {user.username}", min_value=0.0, value=float(user.monthly_vacation_days), step=0.1, format="%.1f", key=f"monthly_days_{user.id}")
                    with col3:
                        new_role = st.selectbox(f"Role for {user.username}", ["Dreher", "Fräser", "Schweißer", "Admin"], index=["Dreher", "Fräser", "Schweißer", "Admin"].index(user.role), key=f"role_{user.id}")
                    with col4:
                        if st.button(f"Update {user.username}", key=f"update_{user.id}"):
                            user.vacation_days = new_vacation_days + calculate_used_vacation_days(user.id)  # Set total vacation days including already taken days
                            user.monthly_vacation_days = new_monthly_days
                            user.role = new_role
                            session.commit()
                            st.experimental_rerun()
                    with col5:
                        if st.button(f"Delete {user.username}", key=f"delete_user_{user.id}"):
                            session.query(User).filter_by(id=user.id).delete()
                            session.commit()
                            st.experimental_rerun()
                            st.success(f"User {user.username} deleted successfully!")
                    st.markdown("<hr>", unsafe_allow_html=True)  # Separation between users

        if admin_choice == "Set Limits":
            st.subheader("Admin View: Set Limits")
            settings = session.query(Settings).first()
            if not settings:
                settings = Settings(dreher_limit=2, fraeser_limit=2, schweisser_limit=2)
                session.add(settings)
                session.commit()

            new_dreher_limit = st.number_input("Set Dreher Limit", min_value=1.0, value=float(settings.dreher_limit), step=0.1, format="%.1f")
            new_fraeser_limit = st.number_input("Set Fräser Limit", min_value=1.0, value=float(settings.fraeser_limit), step=0.1, format="%.1f")
            new_schweisser_limit = st.number_input("Set Schweißer Limit", min_value=1.0, value=float(settings.schweisser_limit), step=0.1, format="%.1f")

            if st.button("Update Limits"):
                settings.dreher_limit = new_dreher_limit
                settings.fraeser_limit = new_fraeser_limit
                settings.schweisser_limit = new_schweisser_limit
                session.commit()
                st.success("Limits updated successfully")

        if admin_choice == "Create User":
            st.subheader("Admin View: Create User")
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            new_vacation_days = st.number_input("Vacation Days", min_value=0.0, step=0.1, format="%.1f")
            new_role = st.selectbox("Role", ["Dreher", "Fräser", "Schweißer", "Admin"])
            new_monthly_days = st.number_input("Monthly Vacation Days", min_value=0.0, value=2.0, step=0.1, format="%.1f")

            if st.button("Create User"):
                register_user(new_username, new_email, new_password, new_vacation_days, new_role, new_monthly_days)
                st.success(f"User {new_username} created successfully!")

    # User view
    if user.role != 'Admin':
        st.subheader("Your Vacation Request")

        # Date and time inputs for vacation start and end
        st.session_state.vacation_start_date = st.date_input(
            "Start Date", 
            value=st.session_state.vacation_start_date or datetime.now().date()
        )
        st.session_state.vacation_end_date = st.date_input(
            "End Date", 
            value=st.session_state.vacation_end_date or datetime.now().date()
        )

        st.session_state.vacation_start_time = st.selectbox("Start Time", valid_times, index=valid_times.index(st.session_state.vacation_start_time))
        st.session_state.vacation_end_time = st.selectbox("End Time", valid_times, index=valid_times.index(st.session_state.vacation_end_time))

        # Validate selection
        if st.session_state.vacation_start_date and st.session_state.vacation_end_date:
            if st.session_state.vacation_start_date > st.session_state.vacation_end_date:
                st.error("End date must be after start date.")
            elif st.session_state.vacation_start_date == st.session_state.vacation_end_date and st.session_state.vacation_start_time >= st.session_state.vacation_end_time:
                st.error("End time must be after start time.")
            else:
                days_requested = calculate_vacation_days(st.session_state.vacation_start_date, st.session_state.vacation_end_date, st.session_state.vacation_start_time, st.session_state.vacation_end_time)
                if days_requested > remaining_days:
                    st.error(f"You only have {remaining_days:.4f} vacation days remaining.")
                else:
                    existing_vacations = session.query(Vacation).filter_by(user_id=user.id).all()
                    overlap = any(
                        (st.session_state.vacation_start_date <= vacation.end_date and st.session_state.vacation_end_date >= vacation.start_date)
                        for vacation in existing_vacations
                    )
                    if overlap:
                        st.error("You already have a vacation scheduled during this period.")
                    else:
                        note = st.text_area("Enter a note for your vacation (optional)")
                        if st.button("Request Vacation"):
                            new_vacation = Vacation(
                                user_id=user.id,
                                start_date=st.session_state.vacation_start_date,
                                end_date=st.session_state.vacation_end_date,
                                start_time=st.session_state.vacation_start_time,
                                end_time=st.session_state.vacation_end_time,
                                status='pending',
                                note=note
                            )
                            session.add(new_vacation)
                            session.commit()
                            st.success("Vacation request submitted!")
                            st.experimental_rerun()

        # Overview of all vacation requests
        st.subheader("Your Vacation Requests Overview")
        vacations = session.query(Vacation).filter_by(user_id=user.id).all()
        if vacations:
            for vacation in vacations:
                status_color = "green" if vacation.status == "approved" else "orange" if vacation.status == "pending" else "red"
                st.markdown(
                    f"<div style='color: {status_color};'>{format_date(vacation.start_date)} to {format_date(vacation.end_date)} "
                    f"({format_time(vacation.start_time)} - {format_time(vacation.end_time)}) - {vacation.status} - Note: {vacation.note}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.write("No vacation requests found.")
