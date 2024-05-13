import streamlit as st
from langchain_community.utilities import SQLDatabase
import tempfile
from sql_agent import SQLAgent
import pandas as pd

def run_query(query):
    '''Run custom or LLM generated query and return the result as a dataframe'''
    try:
        result_cursor = db.run(query, fetch="cursor")
        data = result_cursor.fetchall()
        columns = result_cursor.keys()
        df = pd.DataFrame(data, columns=columns)
        return df
    except:
        return None


def viz_df(query):
    '''Visualize the result of the query'''

    # Retrieve DataFrame from the query
    df = run_query(query)
    if df is None:
        # If the query is invalid, show an error message
        st.error('Query Error, please try again...')
        return
    
    # Column 2 used only for the download button
    visualization, download = st.columns([0.7, 0.3])

    # Visualization column (Column 1)
    popover = visualization.popover('Visualization')
    # Select the type of visualization
    choice = popover.selectbox("Select visualization", ["Table", "Bar chart", "Line chart", "Scatter chart"])

    if choice == "Table":
        st.write(df) # Display the dataframe (st.dataframe does the same thing)
        # Column 2 used only for the download button
        download.download_button("Download as csv", df.to_csv(), "data.csv", "text/csv")

    else:
        # Select the x and y axis to display in the charts
        x = popover.selectbox("Select x-axis", df.columns, index=0)
        y = popover.selectbox("Select y-axis", df.columns, index=1)

        # Display the selected chart
        if choice == "Bar chart":
            st.bar_chart(df, x=x, y=y)
        elif choice == "Line chart":
            st.line_chart(df, x=x, y=y)
        elif choice == "Scatter chart":
            st.scatter_chart(df, x=x, y=y)

# Start of the app, ask the user to upload a database if not present
if "tmp_file_path" not in st.session_state:
    # Set layout for better UI
    st.set_page_config(layout="centered")
    st.title("Upload Database")
    data = st.file_uploader("Upload a database", type=["db"])
    if data:
    # Create a temporary file to save the uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        # Write the content of the uploaded file to the temporary file
            tmp_file.write(data.getvalue())
            st.session_state['tmp_file_path'] = tmp_file.name
            # Rerun the app immediately to show the SQL query tool once the file has been uploaded
            st.rerun()
    button_demo = st.button("Use demo database")
    if button_demo:
        st.session_state['tmp_file_path'] = "data/chinook.db"
        st.rerun()

# If the database is uploaded, show the SQL query tool
if "tmp_file_path" in st.session_state:
    st.set_page_config(layout="wide")

    # Initialize and use the database
    db = SQLDatabase.from_uri(f"sqlite:///{st.session_state['tmp_file_path']}")

    # Used for the header only
    title, button = st.columns([0.85, 0.15])
    title.title("SQL Query Tool")
    button.button("Reset database", on_click=lambda: st.session_state.pop("tmp_file_path"), type="primary")

    # Main layout
    cont1 = st.container()

    # Split the layout into two columns, one for the visualization and the other for the SQL query
    col1, col2 = cont1.columns([0.6, 0.4])
    
    # We start by defining the column 2 that contains the SQL query tool as it is important for the execution order
    with col2:
        st.header("SQL Query")

        # Create a text area for the query and fill it with the custom or LLm generated query
        if 'query' not in st.session_state:
            query = st.text_area("Enter your SQL query here", "")
        else:
            query = st.text_area("Enter your SQL query here", st.session_state['query'])
        
        # Create a button to run the custom query
        run_query_button = st.button("Run query")

        if 'query_output' in st.session_state:
            # Create container to display the output of the LLM with fixed height
            container_output = st.container(height=190)
            container_output.write(st.session_state['query_output'])
    
    # Column 1 contains the visualization of the query
    with col1:
        # If query is not run, show the tables in the database
        if 'query' not in st.session_state and not run_query_button:
            st.write("Tables in the database:")
            st.write(db.get_usable_table_names())

        else:
            if not run_query_button:
                # Run LLM generated query and show visualization
                viz_df(st.session_state['query'])
            else:
                if query:
                    # Run custom query and show visualization
                    st.session_state['query']=query
                    viz_df(st.session_state['query'])
                else:
                    # If query is empty, show the tables in the database
                    st.write(db.get_usable_table_names())

    # Create input to ask LLM to create a query
    prompt = st.chat_input("Enter your question here")

    if prompt:
        # Create loading spinner
        with st.spinner('Wait for it...'):
            try:
                # Create custom SQL agent and ask LLM the question
                agent = SQLAgent(db)
                result = agent.invoke(prompt)

                # Save the output and the query in the session state
                st.session_state['query_output'] = result['output']
                sql_query=agent.get_sql()
                if sql_query:
                    st.session_state['query'] = sql_query[-1]['query']
            except Exception as e:
                # If an error occurs, delete the prompt
                print(e)
                prompt = None
        
        # Rerun the app to show the output and the query
        st.rerun()


