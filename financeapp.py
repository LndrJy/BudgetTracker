import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Advanced Wealth Manager", page_icon="💰", layout="wide")

# --- DATABASE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
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
    conn.commit()
    conn.close()

def add_transaction(date, type, category, amount, notes):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO transactions (date, type, category, amount, notes) VALUES (?, ?, ?, ?, ?)', 
              (date, type, category, amount, notes))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect('finance.db')
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

# Initialize DB
init_db()

# --- ⚠️ CRITICAL FIX: LOAD DATA HERE (AT THE TOP) ---
# We load the data NOW so it is available for the Sidebar AND the Dashboard
df = get_transactions()

# --- SIDEBAR: ADD & DELETE ---
st.sidebar.header("➕ Add Transaction")

# 1. Add Entry Form
tx_date = st.sidebar.date_input("Date", datetime.today())
tx_type = st.sidebar.radio("Type", ["Expense", "Income"])
if tx_type == "Expense":
    options = ["Food", "Transport", "Rent", "Utilities", "Entertainment", "Shopping", "Other"]
else:
    options = ["Salary", "Freelance", "Investment", "Gift", "Other"]
tx_category = st.sidebar.selectbox("Category", options)
tx_amount = st.sidebar.number_input("Amount", min_value=0.01, format="%.2f")
tx_notes = st.sidebar.text_area("Notes (Optional)")

if st.sidebar.button("Add Entry"):
    add_transaction(tx_date, tx_type, tx_category, tx_amount, tx_notes)
    st.sidebar.success("Entry Added!")
    st.rerun()

st.sidebar.divider()

# 2. Delete Entry Form
st.sidebar.header("🗑️ Delete Transaction")
if not df.empty:
    # Create the lookup dictionary
    transaction_options = {f"{row['id']}: {row['category']} - ₱{row['amount']} ({row['date']})": row['id'] for index, row in df.iterrows()}
    
    # Selectbox to choose item
    selected_option = st.sidebar.selectbox("Select Entry to Remove", list(transaction_options.keys()))
    
    # Get the ID from the selection
    selected_id = transaction_options[selected_option]
    
    if st.sidebar.button("Delete Entry"):
        delete_transaction(selected_id)
        st.sidebar.warning(f"Deleted Transaction ID: {selected_id}")
        st.rerun()
else:
    st.sidebar.info("No entries to delete.")

# --- MAIN DASHBOARD: ANALYTICS ---
st.title("💰 Personal Wealth Manager")

# Logic check: Do we have data?
if not df.empty:
    
    # --- 0. DATE FILTER (The New Feature) ---
    st.sidebar.divider()
    st.sidebar.header("⏳ Time Filters")
    
    # We convert the 'date' column to datetime objects immediately for filtering
    df['date'] = pd.to_datetime(df['date'])
    
    # Get the earliest and latest dates in your data
    min_date = df['date'].min()
    max_date = df['date'].max()
    
    # Create a slider or date input
    # default value is a tuple: (start_date, end_date)
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # FILTER LOGIC: Only filter if the user selected two dates (Start & End)
    if len(date_range) == 2:
        start_date, end_date = date_range
        # Convert inputs to datetime64[ns] to match Pandas format
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # The Mask: "Keep rows where date is >= Start AND date <= End"
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        filtered_df = df.loc[mask]
    else:
        filtered_df = df # Fallback if date selection is incomplete
        
    # --- 0.5 EXPORT BUTTON (The "Backup") ---
    # We create a CSV string from the filtered data
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        "📥 Download CSV",
        csv,
        "finance_data.csv",
        "text/csv",
        key='download-csv'
    )

    # --- FROM HERE ON, WE USE 'filtered_df' INSTEAD OF 'df' ---
    
    # --- A. DATA PROCESSING ---
    income_df = filtered_df[filtered_df['type'] == "Income"]
    expense_df = filtered_df[filtered_df['type'] == "Expense"]
    
    total_income = income_df['amount'].sum()
    total_expense = expense_df['amount'].sum()
    remaining_budget = total_income - total_expense
    
    # --- B. KPI CARDS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Income", f"₱{total_income:,.2f}")
    with col2:
        st.metric("Expense", f"₱{total_expense:,.2f}", delta=-total_expense, delta_color="inverse")
    with col3:
        st.metric("Net Flow", f"₱{remaining_budget:,.2f}", delta=remaining_budget)
        
    st.divider()
    
    # --- C. CHARTS ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Expense Breakdown")
        if not expense_df.empty:
            expense_by_cat = expense_df.groupby("category")["amount"].sum().reset_index()
            fig_pie = px.pie(expense_by_cat, values="amount", names="category", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expenses in this time range.")

    with c2:
        st.subheader("Cash Flow Trend")
        
        if not filtered_df.empty:
            # 1. THE VIEW SELECTOR
            # We add a radio button but display it horizontally to save space
            freq_choice = st.radio("View By:", ["Daily", "Weekly", "Monthly"], 
                                   horizontal=True, 
                                   label_visibility="collapsed") # Hides the label "View By"
            
            # 2. RESAMPLING LOGIC (The Magic)
            # Pandas needs a Datetime Index to resample time series
            chart_df = filtered_df.copy()
            chart_df = chart_df.set_index('date')
            
            # Map the user choice to Pandas frequency codes
            # 'D' = Daily, 'W' = Weekly, 'ME' = Month End
            freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}
            selected_freq = freq_map[freq_choice]
            
            # Group by Time AND Type (Income/Expense)
            # .groupby([pd.Grouper(freq=selected_freq), 'type']) matches time buckets
            resampled_df = chart_df.groupby([pd.Grouper(freq=selected_freq), 'type'])['amount'].sum().reset_index()
            
            # 3. THE CHART
            fig_bar = px.bar(
                resampled_df, 
                x="date", 
                y="amount", 
                color="type", 
                color_discrete_map={"Income": "green", "Expense": "red"},
                barmode='group',
                title=f"Cash Flow ({freq_choice})"
            )
            
            # Make the X-axis smart (don't show every single date label if it's crowded)
            fig_bar.update_xaxes(dtick=selected_freq) 
            
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No data available.")

    st.divider()

    # --- D. RECENT TRANSACTIONS TABLE ---
    st.subheader("📝 Transaction Log")
    
    display_df = filtered_df[['id', 'date', 'type', 'category', 'amount', 'notes']].copy()
    
    # Sort so newest is on top
    display_df = display_df.sort_values(by="date", ascending=False)
    
    # Create row numbers
    display_df.reset_index(drop=True, inplace=True)
    display_df.index = display_df.index + 1 
    
    # Format date for display
    display_df['date'] = display_df['date'].dt.strftime('%B %d, %Y')
    
    st.dataframe(
        display_df,
        column_config={
            "id": None, 
            "amount": st.column_config.NumberColumn("Amount", format="₱%.2f"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
        use_container_width=True
    )

else:
    st.info("No transactions found. Add one in the sidebar to start tracking!")