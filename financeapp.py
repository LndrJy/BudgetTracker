import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Advanced Wealth Manager", page_icon="💰", layout="wide")

# --- DATABASE ENGINE (The "Backend") ---
# We use functions to handle the database so we don't lock the file
def init_db():
    # Connect to the database file (it creates it if it doesn't exist)
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Create Table using SQL
    # We store: ID, Date, Type (Income/Expense), Category, Amount, Notes
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            notes TEXT
        )
    ''')
    conn.commit() # Save changes
    conn.close()

def add_transaction(date, type, category, amount, notes):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    # SQL Injection prevention: We use ? as placeholders
    c.execute('INSERT INTO transactions (date, type, category, amount, notes) VALUES (?, ?, ?, ?, ?)', 
              (date, type, category, amount, notes))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect('finance.db')
    # Pandas can read SQL directly! This is super powerful.
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

# Initialize DB on startup
init_db()

# --- SIDEBAR: INPUT FORM (The "Create" Step) ---
st.sidebar.header("➕ Add Transaction")

# 1. Inputs
tx_date = st.sidebar.date_input("Date", datetime.today())
tx_type = st.sidebar.radio("Type", ["Expense", "Income"])

# Dynamic categories based on type
if tx_type == "Expense":
    options = ["Food", "Transport", "Rent", "Utilities", "Entertainment", "Shopping", "Other"]
else:
    options = ["Salary", "Freelance", "Investment", "Gift", "Other"]
    
tx_category = st.sidebar.selectbox("Category", options)
tx_amount = st.sidebar.number_input("Amount", min_value=0.01, format="%.2f")
tx_notes = st.sidebar.text_area("Notes (Optional)")

# 2. Submit Button
if st.sidebar.button("Add Entry"):
    # Convert date to string for SQLite
    add_transaction(tx_date, tx_type, tx_category, tx_amount, tx_notes)
    st.sidebar.success("Entry Added!")
    # We don't need to rerun explicitly; Streamlit handles the state, 
    # but the data table needs to refresh next time it loads.

# --- MAIN DASHBOARD (The "Read" Step) ---
st.title("💰 Personal Wealth Manager")

# 3. Load Data
df = get_transactions()

if not df.empty:
    # 4. Display the Data Frame
    st.subheader("📝 Recent Transactions")
    
    # Sort by date (newest first)
    df = df.sort_values(by="date", ascending=False)
    
    # Show the table
    st.dataframe(df, use_container_width=True)
else:
    st.info("No transactions found. Add one in the sidebar!")