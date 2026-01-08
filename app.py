import streamlit as st
import pandas as pd
import plotly.express as px
import bcrypt
import json
import os
from fpdf import FPDF
from datetime import datetime

# ------------------ THEME ------------------ #
st.set_page_config(page_title="Expense Tracker", layout="wide")

st.markdown("""
    <style>
    .main {
        background-color:#f5f7fa;
    }
    .stButton>button {
        background-color:#4CAF50;
        color:white;
        border-radius:8px;
    }
    .css-10trblm {
        color:#4CAF50;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💰 Personal Expense & Income Dashboard")

# ------------------ USER SYSTEM ------------------ #
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

def create_user(username, password):
    users = load_users()
    if username in users:
        return False
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = hashed
    save_users(users)
    return True

def authenticate(username, password):
    users = load_users()
    if username not in users:
        return False
    return bcrypt.checkpw(password.encode(), users[username].encode())


# ------------------ USER SPECIFIC DATA ------------------ #
def get_user_file(username):
    os.makedirs("data", exist_ok=True)
    return f"data/{username}_data.csv"

def load_data(username):
    file = get_user_file(username)
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=["Date", "Type", "Category", "Amount"])

def save_data(username, df):
    file = get_user_file(username)
    df.to_csv(file, index=False)


# ------------------ LOGIN & REGISTER ------------------ #
menu = ["Login", "Register"]
choice = st.sidebar.selectbox("Menu", menu)

if "user" not in st.session_state:
    st.session_state.user = None

if choice == "Register":
    st.subheader("Create Account")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Register"):
        if create_user(u, p):
            st.success("Account created. Please login now.")
        else:
            st.error("Username already exists")

elif choice == "Login":
    st.subheader("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(u, p):
            st.session_state.user = u
            st.success(f"Welcome {u}")
        else:
            st.error("Invalid credentials")


# ------------------ MAIN DASHBOARD ------------------ #
if st.session_state.user:

    username = st.session_state.user
    st.sidebar.success(f"Logged in as {username}")

    df = load_data(username)

    st.header("➕ Add New Transaction")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        date = st.date_input("Date")
    with c2:
        t = st.selectbox("Type", ["Income", "Expense"])
    with c3:
        category = st.selectbox("Category",
                                ["Salary","Food","Transport","Shopping","Bills","Health","Other"])
    with c4:
        amount = st.number_input("Amount", min_value=1.0)

    if st.button("Save Transaction"):
        new = pd.DataFrame({
            "Date":[date],
            "Type":[t],
            "Category":[category],
            "Amount":[amount]
        })
        df = pd.concat([df, new], ignore_index=True)
        save_data(username, df)
        st.success("Transaction saved")

    st.subheader("📋 Your Transactions")
    st.dataframe(df, use_container_width=True)


    if not df.empty:

        income = df[df["Type"]=="Income"]["Amount"].sum()
        expense = df[df["Type"]=="Expense"]["Amount"].sum()
        balance = income - expense

        c1,c2,c3 = st.columns(3)
        c1.metric("Total Income", income)
        c2.metric("Total Expense", expense)
        c3.metric("Balance", balance)

        # ---------- BUDGET ALERT ---------- #
        if expense > income:
            st.error("⚠ You are spending more than income!")
        if (df[df["Category"]=="Food"]["Amount"].sum()) > 5000:
            st.warning("🍔 Too much spending on Food this month!")

        # ---------- CHARTS ---------- #
        df["Date"] = pd.to_datetime(df["Date"])
        df["Month"] = df["Date"].dt.to_period("M").astype(str)

        fig1 = px.bar(df, x="Category", y="Amount", color="Type", title="Category Breakdown")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(df, x="Month", y="Amount", color="Type", title="Monthly Trend")
        st.plotly_chart(fig2, use_container_width=True)


        # ---------- PDF Export ---------- #
        def create_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Expense Report", ln=True, align='C')

            for i,row in data.iterrows():
                pdf.cell(200, 8,
                         txt=f"{row['Date']} | {row['Type']} | {row['Category']} | {row['Amount']}",
                         ln=True)
            file = f"report_{username}.pdf"
            pdf.output(file)
            return file

        if st.button("Generate PDF Report"):
            file = create_pdf(df)
            with open(file,"rb") as f:
                st.download_button("Download PDF", f, file_name=file)


        st.download_button("Download CSV", df.to_csv(index=False), "report.csv") 