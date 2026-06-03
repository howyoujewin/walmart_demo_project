import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector

# Set the page to wide mode
st.set_page_config(layout="wide")

# ==========================================
# SECURE LIVE SNOWFLAKE CONNECTION
# ==========================================
def load_snowflake_data(user, password, account, warehouse, database, schema):
    # Connect directly to your Snowflake instance with explicit session contexts
    ctx = snowflake.connector.connect(
        user=user,
        password=password,
        account=account,
        warehouse=warehouse,
        database=database,
        schema=schema,
        session_parameters={
            'QUERY_TAG': 'StreamlitDashboard',
            'QUOTED_IDENTIFIERS_IGNORE_CASE': 'TRUE'
        }
    )
    
    # Force your administrative privileges and namespace routing
    cursor = ctx.cursor()
    cursor.execute("USE ROLE ACCOUNTADMIN;")
    cursor.execute(f"USE WAREHOUSE {warehouse.upper()};")
    cursor.execute(f"USE DATABASE {database.upper()};")
    cursor.execute(f"USE SCHEMA {schema.upper()};")
    cursor.close()
    
    # Return both the dataframe AND the live connection object (ctx) 
    # so we can use the same connection for view-specific queries later
    return ctx

# ==========================================
# SIDEBAR CREDENTIALS & NAVIGATION INPUT
# ==========================================
st.sidebar.header("Snowflake Authentication")
sf_account = st.sidebar.text_input("Account (e.g., xy12345.us-east-1)", value="GRNYART-VDC02605")
sf_user = st.sidebar.text_input("User", value="HOWYOUJEWIN")
sf_password = st.sidebar.text_input("Password", type="password")
sf_warehouse = st.sidebar.text_input("Warehouse", value="COMPUTE_WH")
sf_database = st.sidebar.text_input("Database")
sf_schema = st.sidebar.text_input("Schema")

# Navigation dropdown added directly below connection parameters
view_selection = st.sidebar.selectbox("Select Dashboard View", ["Weekly Sales Overview", "Detailed Breakdown","Total Sales by Stores (Large)","Avg Weekly Sales for Large Stores",'Avg Weekly Sales for Medium Stores','Store 1 Total Sales by Department'])

# Only run the layout once the user provides credentials
if sf_account and sf_user and sf_password and sf_database and sf_schema:
    try:
        # Establish connection and handle session roles
        ctx = load_snowflake_data(sf_user, sf_password, sf_account, sf_warehouse, sf_database, sf_schema)
        st.sidebar.success("Successfully connected to Snowflake!")
    except Exception as e:
        st.error(f"Error connecting to Snowflake: {e}")
        st.stop()
else:
    st.info("← Please enter your Snowflake credentials in the sidebar to populate the dashboard with live metrics.")
    st.stop()


# ==========================================
# DASHBOARD LAYOUT (MULTI-PAGE TRACKS)
# ==========================================

if view_selection == "Weekly Sales Overview":
    
    # 1. Main Header
    st.markdown(
        """
        <div style="border: 2px solid #555; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #555; font-size: 42px; margin: 0;">
                weekly sales by store and holiday
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Pull the specific data needed for this main layout
    query_overview = """
    SELECT 
        STORE_ID, 
        IS_HOLIDAY, 
        SUM(WEEKLY_SALES) as WEEKLY_SALES
    FROM PC_DBT_DB.SILVER.INT_WALMART_SALES_JOINED
    GROUP BY STORE_ID, IS_HOLIDAY
    ORDER BY STORE_ID;
    """
    df = pd.read_sql(query_overview, ctx)
    
    # Format columns explicitly for consistency
    df.columns = [col.upper() for col in df.columns]
    df['STORE_ID'] = df['STORE_ID'].astype(str)
    df['IS_HOLIDAY'] = df['IS_HOLIDAY'].astype(bool)
    df['WEEKLY_SALES'] = df['WEEKLY_SALES'].astype(float)

    # Build the split column layout
    left_col, right_col = st.columns([1, 3], gap="large")

    # Left Side: KPIs and Pie Chart
    with left_col:
        pie_data = df.groupby('IS_HOLIDAY')['WEEKLY_SALES'].sum().reset_index()
        fig_pie = px.pie(
            pie_data, 
            values='WEEKLY_SALES', 
            names='IS_HOLIDAY',
            color='IS_HOLIDAY',
            color_discrete_map={False: '#3b82f6', True: '#6b7280'},
            title="Weekly_Sales by IsHoliday"
        )
        fig_pie.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=250)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        total_sales_bn = df['WEEKLY_SALES'].sum() / 1e9
        st.markdown(
            f"""
            <div style="border: 1px solid #ccc; padding: 20px; text-align: center; margin-bottom: 20px;">
                <h2 style="margin: 0; font-size: 36px; font-weight: bold;">{total_sales_bn:.2f}bn</h2>
                <p style="margin: 0; color: #666; font-size: 14px;">Weekly_Sales</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        st.markdown(
            """
            <div style="border: 1px solid #ccc; padding: 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 36px; font-weight: normal; letter-spacing: 2px;">FALSE</h2>
                <p style="margin: 0; color: #666; font-size: 14px;">First IsHoliday</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # Right Side: Massive Bar Chart
    with right_col:
        chart_data = df.sort_values('STORE_ID')
        fig_bar = px.bar(
            chart_data,
            x='STORE_ID',
            y='WEEKLY_SALES',
            color='IS_HOLIDAY',
            barmode='group',
            color_discrete_map={False: '#3b82f6', True: '#6b7280'},
            title="Weekly_Sales by Store - Copy and IsHoliday"
        )
        
        fig_bar.update_layout(
            xaxis=dict(type='category', title=''),
            yaxis=dict(title='', tickformat='.2s'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            height=600,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_bar.update_yaxes(showgrid=True, gridcolor='#eee')
        st.plotly_chart(fig_bar, use_container_width=True)


elif view_selection == "Detailed Breakdown":
    
    # 2. Secondary View Header
    st.markdown(
        """
        <div style="border: 2px solid #3b82f6; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #3b82f6; font-size: 42px; margin: 0;">
                detailed breakdown metrics
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # ----------------------------------------------------
    # PLACE YOUR NEW SQL QUERY HERE!
    # ----------------------------------------------------
    query_detailed = """
    SELECT * FROM INT_WALMART_SALES_JOINED 
    LIMIT 100; 
    """
    
    try:
        # Run your new query against the open connection
        new_df = pd.read_sql(query_detailed, ctx)
        
        # Display the data as an interactive grid for testing
        st.markdown("### Previewing Live Dataset Query Response")
        st.dataframe(new_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"SQL Compilation Error on detailed view: {e}")

elif view_selection == "Weekly Sales by Stores (Large)":
    
    # 2. Secondary View Header
    st.markdown(
        """
        <div style="border: 2px solid #3b82f6; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #3b82f6; font-size: 42px; margin: 0;">
                weekly sales by store size
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # ----------------------------------------------------
    # PLACE YOUR NEW SQL QUERY HERE!
    # ----------------------------------------------------
    query_size = """
    SELECT
    STORE_ID,
    SUM(WEEKLY_SALES) AS WEEKLY_SALES,
    CASE
        WHEN STORE_SIZE < 20000 THEN 'Small'
        WHEN STORE_SIZE BETWEEN 20000 AND 40000 THEN 'Medium'
        ELSE 'Large'
    END AS STORE_SIZE  
    FROM INT_WALMART_SALES_JOINED 
    GROUP BY STORE_ID, STORE_SIZE
    HAVING STORE_SIZE  > 40000
    ORDER BY STORE_ID; 
    """
    
    try:
        # Run your conditional sizing query against the active Snowflake context
        size_df = pd.read_sql(query_size, ctx)
        
        # Clean up column headers to guarantee matching uppercase keys
        size_df.columns = [col.upper() for col in size_df.columns]
        
        # Sort values by Store ID so the lines connect sequentially from left to right
        size_df['STORE_ID_INT'] = size_df['STORE_ID'].astype(int)
        size_df = size_df.sort_values('STORE_ID_INT')
        size_df['STORE_ID'] = size_df['STORE_ID'].astype(str)
        
        # Build the interactive Plotly Line Chart
        fig_line = px.line(
            size_df,
            x='STORE_ID',
            y='WEEKLY_SALES',
            color='STORE_SIZE',
            markers=True,  # Adds clean circular data points to each vertex
            color_discrete_map={'Small': '#10b981', 'Medium': '#f59e0b', 'Large': '#3b82f6'}, # Styled palette
            title="Weekly Sales Trends by Store Identification and Sizing Class"
        )
        
        # Format axes and remove background clutter
        fig_line.update_layout(
            xaxis=dict(type='category', title='Store ID'),
            yaxis=dict(title='Weekly Sales ($)', tickformat='.2s'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title="Store Footprint Size"),
            height=550,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_line.update_yaxes(showgrid=True, gridcolor='#eee')
        fig_line.update_xaxes(showgrid=True, gridcolor='#f5f5f5')
        
        # Render the interactive line visual onto the screen above the grid table
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Keep your data grid underneath as a tabular breakdown
        st.markdown("### Raw Aggregation Matrix View")
        st.dataframe(size_df[['STORE_ID', 'STORE_SIZE', 'WEEKLY_SALES']], use_container_width=True)
        
    except Exception as e:
        st.error(f"SQL Compilation Error or Plotting Error on size view: {e}")

elif view_selection == "Avg Weekly Sales for Large Stores":
    
    # 2. Secondary View Header
    st.markdown(
        """
        <div style="border: 2px solid #3b82f6; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #3b82f6; font-size: 42px; margin: 0;">
                average weekly sales for large stores
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # ----------------------------------------------------
    # PLACE YOUR NEW SQL QUERY HERE!
    # ----------------------------------------------------
    query_size = """
    WITH Large_Stores AS (
        SELECT
            STORE_ID,
            SUM(WEEKLY_SALES) AS TOTAL_WEEKLY_SALES
        FROM PC_DBT_DB.SILVER.INT_WALMART_SALES_JOINED 
        WHERE STORE_SIZE > 40000  
        GROUP BY STORE_ID
    )
    SELECT
        STORE_ID,
        AVG(TOTAL_WEEKLY_SALES) AS AVG_WEEKLY_SALES_LARGE_STORES
    FROM Large_Stores
    GROUP BY STORE_ID;     
    """
    
    try:
        # Run your conditional sizing query against the active Snowflake context
        size_df = pd.read_sql(query_size, ctx)
        
        # Clean up column headers to guarantee matching uppercase keys
        size_df.columns = [col.upper() for col in size_df.columns]
        
        # Sort values by Store ID so the lines connect sequentially from left to right
        size_df['STORE_ID_INT'] = size_df['STORE_ID'].astype(int)
        size_df = size_df.sort_values('STORE_ID_INT')
        size_df['STORE_ID'] = size_df['STORE_ID'].astype(str)
        
        # Build the interactive Plotly Line Chart
        fig_line = px.line(
            size_df,
            x='STORE_ID',
            y='AVG_WEEKLY_SALES_LARGE_STORES',
            title="Weekly Sales Trends by Store Identification and Sizing Class"
        )
        
        # Format axes and remove background clutter
        fig_line.update_layout(
            xaxis=dict(type='category', title='Store ID'),
            yaxis=dict(title='Weekly Sales ($)', tickformat='.2s'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title="Store Footprint Size"),
            height=550,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_line.update_yaxes(showgrid=True, gridcolor='#eee')
        fig_line.update_xaxes(showgrid=True, gridcolor='#f5f5f5')
        
        # Render the interactive line visual onto the screen above the grid table
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Keep your data grid underneath as a tabular breakdown
        st.markdown("### Raw Aggregation Matrix View")
        st.dataframe(size_df[['STORE_ID', 'AVG_WEEKLY_SALES_LARGE_STORES']], use_container_width=True)        
    except Exception as e:
        st.error(f"SQL Compilation Error or Plotting Error on size view: {e}")


elif view_selection == "Total Sales by Stores (Large)":
    
    # 2. Secondary View Header
    st.markdown(
        """
        <div style="border: 2px solid #3b82f6; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #3b82f6; font-size: 42px; margin: 0;">
                total sales by store size
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # ----------------------------------------------------
    # PLACE YOUR NEW SQL QUERY HERE!
    # ----------------------------------------------------
    query_size = """
    SELECT
    STORE_ID,
    SUM(WEEKLY_SALES) AS TOTAL_SALES,
    CASE
        WHEN STORE_SIZE < 20000 THEN 'Small'
        WHEN STORE_SIZE BETWEEN 20000 AND 40000 THEN 'Medium'
        ELSE 'Large'
    END AS STORE_SIZE  
    FROM INT_WALMART_SALES_JOINED 
    GROUP BY STORE_ID, STORE_SIZE
    HAVING STORE_SIZE  > 40000
    ORDER BY STORE_ID; 
    """
    
    try:
        # Run your conditional sizing query against the active Snowflake context
        size_df = pd.read_sql(query_size, ctx)
        
        # Clean up column headers to guarantee matching uppercase keys
        size_df.columns = [col.upper() for col in size_df.columns]
        
        # Sort values by Store ID so the lines connect sequentially from left to right
        size_df['STORE_ID_INT'] = size_df['STORE_ID'].astype(int)
        size_df = size_df.sort_values('STORE_ID_INT')
        size_df['STORE_ID'] = size_df['STORE_ID'].astype(str)
        
        # Build the interactive Plotly Line Chart
        fig_line = px.line(
            size_df,
            x='STORE_ID',
            y='TOTAL_SALES',
            color='STORE_SIZE',
            markers=True,  # Adds clean circular data points to each vertex
            color_discrete_map={'Small': '#10b981', 'Medium': '#f59e0b', 'Large': '#3b82f6'}, # Styled palette
            title="Weekly Sales Trends by Store Identification and Sizing Class"
        )
        
        # Format axes and remove background clutter
        fig_line.update_layout(
            xaxis=dict(type='category', title='Store ID'),
            yaxis=dict(title='Weekly Sales ($)', tickformat='.2s'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title="Store Footprint Size"),
            height=550,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_line.update_yaxes(showgrid=True, gridcolor='#eee')
        fig_line.update_xaxes(showgrid=True, gridcolor='#f5f5f5')
        
        # Render the interactive line visual onto the screen above the grid table
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Keep your data grid underneath as a tabular breakdown
        st.markdown("### Raw Aggregation Matrix View")
        st.dataframe(size_df[['STORE_ID', 'STORE_SIZE', 'TOTAL_SALES']], use_container_width=True)
        
    except Exception as e:
        st.error(f"SQL Compilation Error or Plotting Error on size view: {e}")

elif view_selection == "Avg Weekly Sales for Medium Stores":
    
    # 2. Secondary View Header
    st.markdown(
        """
        <div style="border: 2px solid #3b82f6; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #3b82f6; font-size: 42px; margin: 0;">
                average weekly sales for medium stores
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # ----------------------------------------------------
    # PLACE YOUR NEW SQL QUERY HERE!
    # ----------------------------------------------------
    query_size = """
    SELECT
    STORE_ID,
    AVG(WEEKLY_SALES) AS AVG_WEEKLY_SALES
    FROM INT_WALMART_SALES_JOINED 
    GROUP BY STORE_ID, STORE_SIZE
    HAVING STORE_SIZE BETWEEN 20000 AND 40000
    ORDER BY STORE_ID; 
    """
    
    try:
        # Run your conditional sizing query against the active Snowflake context
        size_df = pd.read_sql(query_size, ctx)
        
        # Clean up column headers to guarantee matching uppercase keys
        size_df.columns = [col.upper() for col in size_df.columns]
        
        # Sort values by Store ID so the lines connect sequentially from left to right
        size_df['STORE_ID_INT'] = size_df['STORE_ID'].astype(int)
        size_df = size_df.sort_values('STORE_ID_INT')
        size_df['STORE_ID'] = size_df['STORE_ID'].astype(str)
        
        # Build the interactive Plotly Line Chart
        fig_line = px.line(
            size_df,
            x='STORE_ID',
            y='AVG_WEEKLY_SALES',
            title="Average Weekly Sales for Medium Stores"
        )
        
        # Format axes and remove background clutter
        fig_line.update_layout(
            xaxis=dict(type='category', title='Store ID'),
            yaxis=dict(title='Average Weekly Sales ($)', tickformat='.2s'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title="Store Footprint Size"),
            height=550,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_line.update_yaxes(showgrid=True, gridcolor='#eee')
        fig_line.update_xaxes(showgrid=True, gridcolor='#f5f5f5')
        
        # Render the interactive line visual onto the screen above the grid table
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Keep your data grid underneath as a tabular breakdown
        st.markdown("### Raw Aggregation Matrix View")
        st.dataframe(size_df[['STORE_ID', 'AVG_WEEKLY_SALES']], use_container_width=True)
        
    except Exception as e:
        st.error(f"SQL Compilation Error or Plotting Error on size view: {e}")

elif view_selection == "Store 1 Total Sales by Department":
    
    # 2. Secondary View Header
    st.markdown(
        """
        <div style="border: 2px solid #3b82f6; padding: 10px; text-align: center; margin-bottom: 30px;">
            <h1 style="font-weight: 300; color: #3b82f6; font-size: 42px; margin: 0;">
                store 1 total sales by department
            </h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # ----------------------------------------------------
    # PLACE YOUR NEW SQL QUERY HERE!
    # ----------------------------------------------------
    query_size = """
    SELECT
    DEPARTMENT_ID,
    SUM(WEEKLY_SALES) AS TOTAL_DEPT_SALES
    FROM PC_DBT_DB.SILVER.INT_WALMART_SALES_JOINED 
    WHERE STORE_ID = '1'
    GROUP BY DEPARTMENT_ID
    ORDER BY DEPARTMENT_ID; 
    """
    
    try:
        # Run your conditional sizing query against the active Snowflake context
        size_df = pd.read_sql(query_size, ctx)
        
        # Clean up column headers to guarantee matching uppercase keys
        size_df.columns = [col.upper() for col in size_df.columns]
        
        # Sort values by Store ID so the lines connect sequentially from left to right
        size_df['DEPARTMENT_ID_INT'] = size_df['DEPARTMENT_ID'].astype(int)
        size_df = size_df.sort_values('DEPARTMENT_ID_INT')
        size_df['DEPARTMENT_ID'] = size_df['DEPARTMENT_ID'].astype(str)
        
        # Build the interactive Plotly bar Chart
        fig_bar = px.bar(
            size_df,
            x='DEPARTMENT_ID',
            y='TOTAL_DEPT_SALES',
            title="Total Sales by Department for Store 1"
        )
        
        # Format axes and remove background clutter
        fig_bar.update_layout(
            xaxis=dict(type='category', title='Department ID'),
            yaxis=dict(title='Total Department Sales ($)', tickformat='.2s'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title="Store Footprint Size"),
            height=550,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_bar.update_yaxes(showgrid=True, gridcolor='#eee')
        fig_bar.update_xaxes(showgrid=True, gridcolor="#f1f1f1")
        
        # Render the interactive bar visual onto the screen above the grid table
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Keep your data grid underneath as a tabular breakdown
        st.markdown("### Raw Aggregation Matrix View")
        st.dataframe(size_df[['DEPARTMENT_ID', 'TOTAL_DEPT_SALES']], use_container_width=True)
        
    except Exception as e:
        st.error(f"SQL Compilation Error or Plotting Error on size view: {e}")


# Always close the global database context at the absolute tail of the execution block
ctx.close()
