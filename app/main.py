import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app.database import init_db, session, User, Vacation, Settings
from app.user_auth import login_user, register_user
from datetime import date, timedelta, datetime
import calendar

# Datenbank initialisieren
init_db()

# Ensure that settings are initialized
def initialize_settings():
    settings = session.query(Settings).first()
    if not settings:
        settings = Settings(dreher_limit=2, fraeser_limit=2, schweisser_limit=2)
        session.add(settings)
        session.commit()

initialize_settings()

# Funktion zur Überprüfung der Urlaubslimits
def check_vacation_limits(user_role, start_date, end_date):
    settings = session.query(Settings).first()
    if user_role == 'Dreher':
        limit = settings.dreher_limit
    elif user_role == 'Fräser':
        limit = settings.fraeser_limit
    elif user_role == 'Schweißer':
        limit = settings.schweisser_limit
    else:
        return True  # Kein Limit für andere Rollen

    overlapping_vacations = session.query(Vacation).join(User).filter(
        User.role == user_role,
        Vacation.status == 'approved',
        Vacation.start_date <= end_date,
        Vacation.end_date >= start_date
    ).count()

    if overlapping_vacations >= limit:
        return False
    return True

# Funktion zum Berechnen der verwendeten Urlaubstage
def calculate_used_vacation_days(user_id):
    approved_vacations = session.query(Vacation).filter_by(user_id=user_id, status='approved').all()
    used_days = sum((vacation.end_date - vacation.start_date).days + 1 for vacation in approved_vacations)
    return used_days

# Funktion zum Berechnen der verbleibenden Urlaubstage
def calculate_remaining_vacation_days(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    used_days = calculate_used_vacation_days(user_id)
    return user.vacation_days - used_days

# Funktion zum Zurücksetzen der Urlaubsdaten
def reset_vacations():
    session.query(Vacation).delete()
    session.commit()

# Funktion zum Löschen eines bestimmten Urlaubs
def delete_vacation(vacation_id):
    session.query(Vacation).filter(Vacation.id == vacation_id).delete()
    session.commit()

# Funktion zum Löschen eines Benutzers
def delete_user(user_id):
    user_to_delete = session.query(User).filter_by(id=user_id).first()
    if user_to_delete:
        # Löschen aller Urlaubsanfragen des Benutzers
        session.query(Vacation).filter_by(user_id=user_id).delete()
        # Löschen des Benutzers
        session.delete(user_to_delete)
        session.commit()

# Funktion zum Formatieren des Datums
def format_date(d):
    return d.strftime('%d-%m-%Y')

# Funktion zum Hinzufügen von Urlaubstagen am Anfang jedes Monats
def add_monthly_vacation_days():
    today = date.today()
    if today.day == 1:  # Überprüfen, ob heute der erste Tag des Monats ist
        users = session.query(User).all()
        for user in users:
            user.vacation_days += user.monthly_vacation_days  # Hinzufügen von benutzerdefinierten Urlaubstagen
        session.commit()

# Füge die monatlichen Urlaubstage hinzu
add_monthly_vacation_days()

# Streamlit-Layout
st.title("Vacation Manager")

# Login
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.subheader("Login to Your Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        print(f"Trying to log in with username: {username} and password: {password}")
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
        st.write(f"You have {remaining_days} vacation days remaining.")

    # Admin-Ansicht
    if user.role == 'Admin':
        admin_choice = st.sidebar.selectbox("Admin Actions", ["Manage Vacation Requests", "Manage Users", "Set Limits", "Create User"])
        
        if admin_choice == "Manage Vacation Requests":
            st.subheader("Admin View: Vacation Requests")

            # Überschrift für jede Spalte
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 2.5, 1.5])
            with col1:
                st.markdown("**Request Details**")
            with col2:
                st.markdown("**Actions**")
            with col3:
                st.markdown("**Delete**")
            with col4:
                st.markdown("**Update Dates**")
            with col5:
                st.markdown("**Days Left**")

            for vacation in session.query(Vacation).all():
                requester = session.query(User).filter_by(id=vacation.user_id).first()
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 2.5, 1.5])
                with col1:
                    st.write(f"**{requester.username} ({requester.role}):** {format_date(vacation.start_date)} to {format_date(vacation.end_date)} ({vacation.status})")
                    st.write(f"**Note:** {vacation.note}")
                with col2:
                    if vacation.status == 'pending':
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
                with col3:
                    if st.button(f"Delete {vacation.id}", key=f"delete_{vacation.id}"):
                        delete_vacation(vacation.id)
                        session.commit()
                        st.experimental_rerun()
                with col4:
                    new_start_date = st.date_input("Start Date", vacation.start_date, key=f"start_{vacation.id}")
                    new_end_date = st.date_input("End Date", vacation.end_date, key=f"end_{vacation.id}")
                    if st.button(f"Update {vacation.id}", key=f"update_{vacation.id}"):
                        vacation.start_date = new_start_date
                        vacation.end_date = new_end_date
                        session.commit()
                        st.experimental_rerun()
                with col5:
                    requester_remaining_days = calculate_remaining_vacation_days(requester.id)
                    st.write(f"{requester_remaining_days} days left")

            # Knopf zum Zurücksetzen der Urlaubsdaten
            st.markdown("---")
            if st.button("Reset All Vacations"):
                reset_vacations()
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
                        new_vacation_days = st.number_input(f"Set Vacation Days for {user.username}", min_value=0, value=remaining_days, key=f"vac_days_{user.id}")
                        new_monthly_days = st.number_input(f"Monthly Vacation Days for {user.username}", min_value=0, value=user.monthly_vacation_days, key=f"monthly_days_{user.id}")
                    with col3:
                        new_role = st.selectbox(f"Role for {user.username}", ["Dreher", "Fräser", "Schweißer", "Admin"], index=["Dreher", "Fräser", "Schweißer", "Admin"].index(user.role), key=f"role_{user.id}")
                    with col4:
                        if st.button(f"Update {user.username}", key=f"update_{user.id}"):
                            user.vacation_days = new_vacation_days + calculate_used_vacation_days(user.id)  # Gesamte Urlaubstage inklusive bereits genommener Tage setzen
                            user.monthly_vacation_days = new_monthly_days
                            user.role = new_role
                            session.commit()
                            st.experimental_rerun()
                    with col5:
                        if st.button(f"Delete {user.username}", key=f"delete_user_{user.id}"):
                            delete_user(user.id)
                            st.success(f"User {user.username} deleted successfully!")
                            st.experimental_rerun()

        if admin_choice == "Set Limits":
            st.subheader("Admin View: Set Limits")
            settings = session.query(Settings).first()
            if not settings:
                settings = Settings(dreher_limit=2, fraeser_limit=2, schweisser_limit=2)
                session.add(settings)
                session.commit()

            new_dreher_limit = st.number_input("Set Dreher Limit", min_value=1, value=settings.dreher_limit)
            new_fraeser_limit = st.number_input("Set Fräser Limit", min_value=1, value=settings.fraeser_limit)
            new_schweisser_limit = st.number_input("Set Schweißer Limit", min_value=1, value=settings.schweisser_limit)

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
            new_vacation_days = st.number_input("Vacation Days", min_value=0)
            new_role = st.selectbox("Role", ["Dreher", "Fräser", "Schweißer", "Admin"])
            new_monthly_days = st.number_input("Monthly Vacation Days", min_value=0, value=2)

            if st.button("Create User"):
                register_user(new_username, new_email, new_password, new_vacation_days, new_role, new_monthly_days)
                st.success(f"User {new_username} created successfully!")

    # Benutzeransicht
    else:
        st.subheader("Your Vacation Calendar")
        
        # Legende
        st.markdown("""
        <div style='display: flex; justify-content: space-around;'>
            <div style='background-color: green; padding: 5px; color: white;'>Approved</div>
            <div style='background-color: orange; padding: 5px; color: white;'>Pending</div>
            <div style='background-color: red; padding: 5px; color: white;'>Denied</div>
            <div style='background-color: darkblue; padding: 5px; color: white;'>Selected</div>
        </div>
        """, unsafe_allow_html=True)

        today = date.today()

        # Monat und Jahr Auswahl (nur August bis Dezember 2024)
        months = ["August", "September", "October", "November", "December"]
        month_numbers = {month: index + 8 for index, month in enumerate(months)}
        selected_month = st.selectbox("Select Month", months)
        selected_year = 2024

        # Umwandlung des ausgewählten Monats in eine Zahl
        month_index = month_numbers[selected_month]
        
        days_in_month = calendar.monthrange(selected_year, month_index)[1]

        # Kalender für den ausgewählten Monat anzeigen
        cal = calendar.monthcalendar(selected_year, month_index)
        st.write(f"{selected_month} {selected_year}")

        # Kalender-Interaktion
        if 'vacation_start' not in st.session_state:
            st.session_state.vacation_start = None
        if 'vacation_end' not in st.session_state:
            st.session_state.vacation_end = None

        # Angefragte Urlaubszeiten aus der Datenbank abrufen
        requested_vacations = session.query(Vacation).filter_by(user_id=user.id, status='pending').all()
        requested_dates = []
        for vacation in requested_vacations:
            requested_dates.extend([vacation.start_date + timedelta(days=i) for i in range((vacation.end_date - vacation.start_date).days + 1)])

        # Genehmigte Urlaubszeiten aus der Datenbank abrufen
        approved_vacations = session.query(Vacation).filter_by(user_id=user.id, status='approved').all()
        approved_dates = []
        for vacation in approved_vacations:
            approved_dates.extend([vacation.start_date + timedelta(days=i) for i in range((vacation.end_date - vacation.start_date).days + 1)])

        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
                else:
                    day_date = date(selected_year, month_index, day)
                    vacations = session.query(Vacation).filter_by(user_id=user.id, start_date=day_date).all()
                    if vacations:
                        status = vacations[0].status
                        color = "green" if status == 'approved' else "orange" if status == 'pending' else "red"
                    else:
                        color = "white"  # Standardfarbe setzen
                        if st.session_state.vacation_start and st.session_state.vacation_end:
                            if st.session_state.vacation_start <= day_date <= st.session_state.vacation_end:
                                color = "darkblue"
                        elif st.session_state.vacation_start and not st.session_state.vacation_end:
                            if day_date == st.session_state.vacation_start:
                                color = "darkblue"
                        elif day_date in requested_dates:
                            color = "orange"
                        elif day_date in approved_dates:
                            color = "green"

                    if cols[i].button(f"{day}", key=str(day_date), help=f"Select {day_date}", use_container_width=True):
                        if st.session_state.vacation_start is None:
                            st.session_state.vacation_start = day_date
                        elif st.session_state.vacation_end is None:
                            if day_date >= st.session_state.vacation_start:
                                st.session_state.vacation_end = day_date
                            else:
                                st.session_state.vacation_start = day_date
                        else:
                            st.session_state.vacation_start = day_date
                            st.session_state.vacation_end = None
                        st.experimental_rerun()
                    
                    cols[i].markdown(f"<div style='background-color:{color}; padding:5px; font-size:small; text-align:center; border-radius: 5px; height: 40px; line-height: 40px;'>{day}</div>", unsafe_allow_html=True)

        if st.session_state.vacation_start and st.session_state.vacation_end:
            st.write(f"Selected vacation from {format_date(st.session_state.vacation_start)} to {format_date(st.session_state.vacation_end)}")
            if st.session_state.vacation_start > st.session_state.vacation_end:
                st.error("End date must be after start date")
            else:
                days_requested = (st.session_state.vacation_end - st.session_state.vacation_start).days + 1
                note = st.text_area("Enter a note for your vacation (optional)")
                if days_requested > remaining_days:
                    st.error(f"You only have {remaining_days} vacation days remaining.")
                else:
                    if st.button("Request Vacation"):
                        new_vacation = Vacation(user_id=user.id, start_date=st.session_state.vacation_start, end_date=st.session_state.vacation_end, status='pending', note=note)
                        session.add(new_vacation)
                        session.commit()
                        st.success("Vacation request submitted!")
                        st.session_state.vacation_start = None
                        st.session_state.vacation_end = None
                        st.experimental_rerun()

        # Knopf zum Zurücksetzen der Auswahl
        if st.button("Clear Selection"):
            st.session_state.vacation_start = None
            st.session_state.vacation_end = None
            st.experimental_rerun()

        # Übersicht über alle Urlaubsanfragen des Mitarbeiters
        st.subheader("Your Vacation Requests Overview")
        vacations = session.query(Vacation).filter_by(user_id=user.id).all()
        if vacations:
            for vacation in vacations:
                st.write(f"{format_date(vacation.start_date)} to {format_date(vacation.end_date)} - {vacation.status} - Note: {vacation.note}")
        else:
            st.write("No vacation requests found.")
