import mysql.connector
import streamlit as st
import requests
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()


# MySQL database setup
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="test"
)
cursor = db.cursor()

# Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        email VARCHAR(255),
        age INT,
        num_tickets INT,
        museum VARCHAR(255)
    )
""")




def get_ai_response(prompt):
    # Replace with your actual Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    url = os.getenv("GEMINI_API_URL")

    headers = {
        "Content-Type": "application/json",
    }

    params = {
        "key": api_key
    }
    request_data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"You are an AI assistant helping users book museum tickets. You need to collect their name, age, number of tickets, and chosen museum. If their input is invalid or unclear, explain why and offer suggestions. The user said: {prompt}"
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=request_data, params=params)

    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"Error: {response.status_code} - {response.text}"



# Predefined responses and validations
museums = ["Louvre", "British Museum", "Metropolitan Museum of Art", "Hermitage"]
max_tickets = 10

def process_user_input(name, email, age, num_tickets, museum):
    if not re.match(r'^[A-Za-z\s\'-]+$', name):
        return "Invalid name. Please enter a valid name using only letters, spaces, hyphens, and apostrophes."
    if not re.match(r'^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$', email):
        return "Invalid email address. Please enter a valid email."
    if not age.isdigit() or int(age) <= 0 or int(age) >= 120:
        return "Invalid age. Please enter a valid age between 1 and 119."
    if not num_tickets.isdigit() or int(num_tickets) <= 0 or int(num_tickets) > max_tickets:
        return "Invalid number of tickets. Please enter a valid number between 1 and 10."
    if museum not in museums:
        return f"Invalid museum. Please choose one of the following museums: {', '.join(museums)}."
    
    try:
        cursor.execute("INSERT INTO ticket_bookings (name, email, age, num_tickets, museum) VALUES (%s, %s, %s, %s, %s)", (name, email, int(age), int(num_tickets), museum))
        db.commit()
        return "Booking successful!"
    except mysql.connector.Error as e:
        return f"Error: {e}"

data = {"name": None, "email": None, "age": None, "num_tickets": None, "museum": None}

def process_user_input_2(user_input, state):
    if state == "initial":
        if user_input != "":
            return get_ai_response(f"Start by asking for the user's name. The user said: '{user_input}'"), "name"
        else:
            return "Please enter your name to begin.", "initial"

    elif state == "name":
        if re.match(r'^[A-Za-z\s\'-]+$', user_input):
            data["name"] = user_input
            return "Great! Now, what's your email?", "email"
        else:
            return get_ai_response(f"The user provided '{user_input}' as their name, which seems invalid. Explain why and ask again."), "name"

    elif state == "email":
        if re.match(r'^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$', user_input):
            data["email"] = user_input
            return "Got it! Now, what's your age?", "age"
        else:
            return get_ai_response(f"The user provided '{user_input}' as their email, which seems invalid. Explain why and ask again."), "email"
    
    elif state == "age":
        if user_input.isdigit() and 0 < int(user_input) < 120:
            data["age"] = int(user_input)
            state = "tickets"
            return "Great! How many tickets would you like to book?", "tickets"
        else:
            return get_ai_response(f"The user provided '{user_input}' as their age, which seems invalid. Explain why and ask again."), "age"
    
    elif state == "tickets":
        if user_input.isdigit() and 0 < int(user_input) <= max_tickets:
            data["num_tickets"] = int(user_input)
            state = "museum"
            return "Perfect! Which museum would you like to visit?", "museum"
        else:
            return get_ai_response(f"The user provided '{user_input}' as the number of tickets, which seems invalid. Explain why and ask again."), "tickets"
    
    elif state == "museum":
        if user_input in museums:
            data["museum"] = user_input
            state = "complete"
            try:
                cursor.execute("INSERT INTO ticket_bookings (name, email, age, num_tickets, museum) VALUES (%s, %s, %s, %s, %s)", (data["name"], data["email"], data["age"], data["num_tickets"], data["museum"]))
                db.commit()
                return "Great choice! Your booking is complete.", "complete"
            except mysql.connector.Error as e:
                return f"Error: {e}"
        else:
            return get_ai_response(f"The user provided '{user_input}' as the museum, which seems invalid. Explain why and ask again."), "museum"
    
    else:
        return "Thank you for providing all the information!"


def main():
    # Initialize the data dictionary and conversation state
    state = "initial"

    st.title("Museum Ticket Booking")
    
    st.write("Please fill in the following details to book your tickets:")
    
    manual_form = st.checkbox("Fill in the form manually")
    
    if manual_form:
        with st.form("booking_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            age = st.text_input("Age")
            num_tickets = st.text_input("Number of Tickets")
            museum = st.selectbox("Museum", museums)
            
            submit = st.form_submit_button("Book Tickets")
            
            if submit:
                result = process_user_input(name, email, age, num_tickets, museum)
                st.write(result)
    else:
        st.write("Let's fill in the details together!")

        while state != "complete":
            user_input = st.text_input(f"Please enter your {state.capitalize()}: ", key=state).strip()
            ai_response, state = process_user_input_2(user_input, state)
            st.write(ai_response)

if __name__ == "__main__":
    main()