import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import requests
import os

client = MongoClient("mongodb://localhost:27017/")
db = client.tax_calculator
users_collection = db.users
tax_history_collection = db.tax_history
gst_history_collection = db.gst_history

def calculate_tax(taxable_income, regime='old'):
    tax = 0
    slab_details = []
    
    if regime == 'old':
        slabs = [
            (0, 250000, 0),
            (250000, 500000, 0.05),
            (500000, 750000, 0.20),
            (750000, 1000000, 0.20),
            (1000000, 1250000, 0.30),
            (1250000, 1500000, 0.30),
            (1500000, float('inf'), 0.30)
        ]
    else:
        slabs = [
            (0, 250000, 0),
            (250000, 500000, 0.05),
            (500000, 750000, 0.10),
            (750000, 1000000, 0.15),
            (1000000, 1250000, 0.20),
            (1250000, 1500000, 0.25),
            (1500000, float('inf'), 0.30)
        ]
    
    remaining_income = taxable_income
    for lower, upper, rate in slabs:
        if taxable_income > lower:
            amount = min(remaining_income, upper - lower)
            tax_amount = amount * rate
            slab_details.append({
                "range": f"{lower+1} - {upper}",
                "amount": amount,
                "rate": rate,
                "tax": tax_amount
            })
            tax += tax_amount
            remaining_income -= amount
        else:
            break

    cess = tax * 0.04
    total_tax = tax + cess
    return total_tax, slab_details

def signup(username, password, age, email):
    if users_collection.find_one({"username": username}):
        return False, "Username already exists"
    user = {"username": username, "password": password, "age": age, "email": email}
    users_collection.insert_one(user)
    return True, "Signup successful"

def login(username, password):
    user = users_collection.find_one({"username": username, "password": password})
    return user is not None

def get_financial_advice(query):
    api_key = "AIzaSyCiRPzAi5yuO4_ryVNob62BvotbmKJObD0"
    model = "gemini-1.5-pro" 
    
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": query}]}]}

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("candidates", [{}])[0].get("content", "No advice found.")
    return f"Error fetching advice: {response.text}"


st.title("Indian Income Tax Calculator")

menu = st.sidebar.radio("Navigation", ["Sign In", "Sign Up", "Tax Calculation", "Tax History", "GST Calculator", "Financial Chatbot"])


if menu == "Sign Up":
    st.header("Signup")
    signup_username = st.text_input("Username", key="signup_username")
    signup_password = st.text_input("Password", type="password", key="signup_password")
    signup_age = st.number_input("Age", min_value=18, key="signup_age")
    signup_email = st.text_input("Email", key="signup_email")
    if st.button("Signup"):
        success, msg = signup(signup_username, signup_password, signup_age, signup_email)
        st.success(msg) if success else st.sidebar.error(msg)
        
elif menu == "Sign In":
    st.header("Login")
    login_username = st.text_input("Username", key="login_username")
    login_password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        if login(login_username, login_password):
            st.session_state.logged_in = True
            st.session_state.username = login_username
            st.success("Logged in successfully")
        else:
            st.error("Invalid credentials")

if menu == "Tax Calculation" and st.session_state.get("logged_in"):
    st.header(f"Welcome {st.session_state.username}!")
    
    st.subheader("Enter Your Income Details")
    basic_salary = st.number_input("Basic Salary (₹)", min_value=0, value=0)
    hra = st.number_input("HRA (₹)", min_value=0, value=0)
    bonus = st.number_input("Bonus (₹)", min_value=0, value=0)
    other_income = st.number_input("Other Income (₹)", min_value=0, value=0)
    
    st.subheader("Enter Deductions")
    st.write("Standard Deduction: ₹50,000")
    deduction_80C = st.number_input("80C Deduction (₹)", min_value=0, value=0, max_value=150000)
    deduction_80D = st.number_input("80D Deduction (₹)", min_value=0, value=0)
    
    st.subheader("Select Tax Regime")
    regime = st.radio("Choose Tax Regime", ("Old", "New"))
    
    if st.button("Calculate Tax"):
        gross_income = basic_salary + hra + bonus + other_income
        taxable_income = gross_income - 50000
        if regime == "Old":
            taxable_income -= (deduction_80C + deduction_80D)
        tax_payable, slab_breakdown = calculate_tax(taxable_income, regime.lower())
        tax_history_collection.insert_one({
            "username": st.session_state.username,
            "basic_salary": basic_salary,
            "hra": hra,
            "bonus": bonus,
            "other_income": other_income,
            "deduction_80C": deduction_80C,
            "deduction_80D": deduction_80D,
            "standard_deduction": 50000,
            "gross_income": gross_income,
            "taxable_income": taxable_income,
            "regime": regime,
            "total_tax": tax_payable,
            "slab_breakdown": slab_breakdown,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

if menu == "Tax History" and st.session_state.get("logged_in"):
    st.header("Tax History")
    history = tax_history_collection.find({"username": st.session_state.username})
    history_df = pd.DataFrame(list(history))
    if not history_df.empty:
        st.dataframe(history_df[["date", "gross_income", "taxable_income", "regime", "total_tax"]])
        if st.button("Download Report as CSV"):
            history_df.to_csv("tax_report.csv", index=False)
            st.success("Report downloaded as tax_report.csv")

def calculate_gst(amount, gst_rate):
    gst_amount = (amount * gst_rate) / 100
    total_amount = amount + gst_amount
    return gst_amount, total_amount

if menu == "GST Calculator" and st.session_state.get("logged_in"):
    st.header("GST Calculator")
    amount = st.number_input("Enter Amount (₹)", min_value=0.0, value=0.0)
    gst_rate = st.number_input("Enter GST Rate (%)", min_value=0.0, max_value=100.0, value=18.0)
    
    if st.button("Calculate GST"):
        gst_amount, total_amount = calculate_gst(amount, gst_rate)
        gst_history_collection.insert_one({
            "username": st.session_state.username,
            "amount": amount,
            "gst_rate": gst_rate,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.write(f"GST Amount: ₹{gst_amount:.2f}")
        st.write(f"Total Amount (Including GST): ₹{total_amount:.2f}")
    
    st.subheader("GST Calculation History")
    gst_history = gst_history_collection.find({"username": st.session_state.username})
    gst_df = pd.DataFrame(list(gst_history))
    if not gst_df.empty:
        st.dataframe(gst_df[["date", "amount", "gst_rate", "gst_amount", "total_amount"]])
        if st.button("Download GST Report as CSV"):
            gst_df.to_csv("gst_report.csv", index=False)
            st.success("Report downloaded as gst_report.csv")

if menu == "Financial Chatbot":
    st.header("Financial Chatbot")
    user_query = st.text_area("Ask your financial question:")
    if st.button("Get Advice"):
        advice = get_financial_advice(user_query)
        st.write(advice)
