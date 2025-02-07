import streamlit as st
import pandas as pd
from routers.users import chat
import plotly.graph_objects as go
import sqlparse
from utility.chat_helper import data_processing,delete_cache_folder
import sqlite3
import asyncio
import io
import json
import os
import random
import time
import re
from utility.static import add_plot,load_dataframe


st.set_page_config(page_title="Quin", layout="wide")
st.markdown("""
    <div style='text-align: center; margin-top:-50px; margin-bottom: 5px;margin-left: -50px;'>
    <h2 style='font-size: 60px; font-family: Courier New, monospace;
                    letter-spacing: 2px; text-decoration: none;'>
    <img src="https://acis.affineanalytics.co.in/assets/images/logo_small.png" alt="logo" width="70" height="60">
    <span style='background: linear-gradient(45deg, #ed4965, #c05aaf);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            text-shadow: none;'>
                    Quin
    </span>
    <span style='font-size: 60%;'>
    <sup style='position: relative; top: 5px; color:white ;'>by Affine</sup> 
    </span>
    </h2>
    </div>
    """, unsafe_allow_html=True)


st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 50px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        color: rgb(20, 20, 20); /* Dark text color */
        font-weight: 900; /* Bold text */
        white-space: pre-wrap;
        background-color: rgb(240, 240, 240); /* Light grey background for inactive tabs */
        border-radius: 17px 17px 17px 17px;
        gap: 1px;
        padding-top: -10px;
        padding-bottom: -10px;
        padding-left: 10px;
        padding-right: 10px;
        transition: background-color 0.3s, color 0.3s;
    }

    /* Hover effect with light green background */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgb(204, 255, 204); /* Light green background on hover */
    }

    .stTabs [aria-selected="true"] {
        color: rgb(255, 255, 255); /* White text for active tab */
        font-weight: 900; /* Bold font for active tab */
        background-color: rgb(0, 123, 255); /* Blue background for active tab */
        border-bottom: 3px solid rgb(0, 123, 255); /* Bottom border matches the active color */
    }
</style>
""", unsafe_allow_html=True)


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "history_manager" not in st.session_state:
    st.session_state.history_manager=[]

if "tool_define" not in st.session_state:
    st.session_state.tool_define=None

if "data_dictionary_prompt" not in st.session_state:
    st.session_state.data_dictionary_prompt=None

if "date_range" not in st.session_state:
    st.session_state.date_range=None

if "file_name" not in st.session_state:
    st.session_state.file_name=None

if "faq" not in st.session_state:
    st.session_state.faq=pd.DataFrame()





# Constants
BASE_PATH = os.getcwd()
# faq_streamlit_genai/faq.csv
FAQ_FILE = os.path.join(BASE_PATH, "faq_streamlit_genai", "faq.csv")
LOGO_PATH = "Siemens_Energy_logo.png"

if st.session_state.faq.empty:
    st.session_state.faq=pd.read_csv(FAQ_FILE, encoding="ISO-8859-1")

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Siemens_Energy_logo.svg/1200px-Siemens_Energy_logo.svg.png")
    if os.path.exists("database.db"):
        uploaded_file = st.file_uploader("Please upload a file", type=["xlsx","csv"])
        st.info("The data is already loaded. To load new data, you can upload a file here. Otherwise, feel free to ignore this and proceed to ask your query.")
    else:
        uploaded_file = st.file_uploader("Please upload a file", type=["xlsx","csv"])
        
        
    if uploaded_file is not None and st.session_state.file_name==None:
        if uploaded_file.type=="xlsx":
            try:
                df = pd.read_excel(uploaded_file,sheet_name="Sample data")
                data_processing(df)
                st.write("Uploaded file details:")
                st.write(f"File name: {uploaded_file.name}")
                st.session_state.file_name="process_df.csv"
                st.write(f"File size: {uploaded_file.size / 1024:.2f} KB")
                # st.rerun()
            except Exception as e:
                st.error(f"Error occurred at data preprocessing :: {e}")
        else:
            try:
                df = pd.read_csv(uploaded_file)
                data_processing(df)
                st.write("Uploaded file details:")
                st.write(f"File name: {uploaded_file.name}")
                st.session_state.file_name="process_df.csv"
                st.write(f"File size: {uploaded_file.size / 1024:.2f} KB")

                # st.rerun()
            except Exception as e:
                st.error(f"Error occurred at data preprocessing :: {e}")


    button=st.button("Delete the Autogen Cache")
    if button:
        delete_cache_folder()
        st.info("Delete the autogen cache succesfully.")

if os.path.exists("database.db"):
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        if message["role"]=="user":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        else:
            if message["role"]=="assistant":
                if message["content"]['flow']==1:
                    tab1,tab2,tab3,tab4=st.tabs(['Insights',"📈 Plot","SQL Query","🗃 Data"])
                    # Tab-1 :: Insights
                    tab1.markdown(message["content"]['insight'])
                    tab1.info(message["content"]['message'])
                    
                    # Tab- 2 :: Plot
                    if message['content']['plot']!="No Plot":
                        with tab2:
                            st.image(message['content']['plot'], caption="Visualization", use_container_width=True)
                    else:
                        tab2.markdown("No Plots")
                        
                    # Tab- 3 :: SQL Query
                    sql_query=message["content"]['sql_query']
                    formatted_query = sqlparse.format(sql_query, reindent=True, keyword_case='upper')
                    tab3.markdown(f"""```bash 
                    {formatted_query}
                    """)
                    # with tab3.expander("See sql query explanation.."):
                    #         st.markdown(message["content"]['sql_query_exp'])
                    
                    # Tab- 4 :: Dataframe
                    if message["content"]['df']=="":
                        data_list=""
                        tab4.write("No Data")
                    else:
                        with tab4:
                            data_list=message["content"]['df']
                            data_list=os.path.join(BASE_PATH,data_list).replace("\\","//")
                            print("data_list ::",data_list  )
                            df=load_dataframe(data_list)
                            st.dataframe(df)

                else:
                    tab1,tab2,tab3,tab4=st.tabs(['Insights',"📈 Plot","SQL Query","🗃 Data"])
                    # Tab-1 :: Insights
                    tab1.markdown(message["content"]['insight'])
                    tab1.info(message["content"]['message'])
                    
                    # Tab- 2 :: Plot
                    if message['content']['plot']!="":
                        fig = go.Figure(data=message['content']['plot'], layout=message['content']['plot'])
                        tab2.plotly_chart(fig)
                    else:
                        tab2.markdown("No Plots")
                    # Tab- 3 :: SQL Query
                    sql_query=message["content"]['sql_query']
                    formatted_query = sqlparse.format(sql_query, reindent=True, keyword_case='upper')
                    tab3.markdown(f"""```bash 
                    {formatted_query}
                    """)
                    with tab3.expander("See sql query explanation.."):
                            st.markdown(message["content"]['sql_query_exp'])
                    
                    # Tab- 4 :: Dataframe
                    if message["content"]['df']=="":
                        data_list=""
                        tab4.write("No Data")
                    else:
                        tab4.dataframe(message["content"]['df'])
                    

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        escaped_query = re.escape(prompt)
        matched_rows = st.session_state.faq[st.session_state.faq["Questions"].str.contains(escaped_query, case=False, na=False)]
        if not matched_rows.empty:
            flow=1
            print(f"-----------------------------{flow}----------------------------")
            # print(matched_rows)
            row = matched_rows.iloc[0]
             # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)
            import random
            import time
            response_time=random.randint(5,10)
            # Display assistant response in chat message container
            with st.spinner():
                time.sleep(response_time)
                # sleep for some sec
                response={'question': row['Questions'], 
                'sql_query': row['SQL Query'] ,
                'sql_query_explanation':"", #matched_rows['sql_query_explanation'] ,
                "plotly":row['Plot'] ,
                'insights': row['Insights'] , 
                'db_result':  row['Data']}
                
            
            tab1,tab2,tab3,tab4=st.tabs(['Insights',"📈 Plot","SQL Query","🗃 Data"])
            insights=""
            

            if type(response['insights'])==list:
                for i,insight in enumerate(response['insights']):
                    insights+=f"{i+1}. "+insight +"\n\n"
                message= f"Response Time :: {response_time:.2f} seconds"
            else:
                insights=response['insights'] +"\n\n"
                message= f"Response Time :: {response_time:.2f} seconds"
            # Tab 1 :: Insights
            tab1.markdown(insights)
            tab1.info(message)

            # Tab 2 :: Plots
            plotly=str(row.get('Plot', '')).replace('"', '').strip()
            print("plotly ::",plotly)
            if plotly!="No Plot":
                plotly=os.path.join(BASE_PATH,plotly).replace("\\","//")
                print("Plot ::",plotly)
                with tab2:
                    st.image(plotly, caption="Visualization", use_container_width=True)
            else:
                tab2.markdown("No Plots")
            
            # Tab 3 :: SQL Query
            sql_query=response['sql_query']
            sql_explanation=response['sql_query_explanation']
            tab3.markdown(f"""```bash 
                    {sql_query}
                    """)
            # with tab3.expander("See sql query explanation.."):
            #     st.markdown(sql_explanation)
            
            # Dataframe
            if response['db_result']=="":
                data_list=""
                tab4.write("No Data")
            else:
                with tab4:
                    data_list=response['db_result']
                    data_list=os.path.join(BASE_PATH,data_list).replace("\\","//")
                    print("data_list ::",data_list  )
                    df=load_dataframe(data_list)
                    print(df)
                    st.dataframe(df)
                    

            data1={"insight":insights,
            "plot":plotly,
            "sql_query":sql_query,
            "sql_query_exp":sql_explanation,
            "df":data_list,
            "message":message,
            "flow":flow
            }
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": data1})
            st.rerun()

            
        else:
            flow=0
            print(f"-----------------------------{flow}----------------------------")
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            # Display assistant response in chat message container
            with st.spinner():
                response= chat(prompt) # await
            
            tab1,tab2,tab3,tab4=st.tabs(['Insights',"📈 Plot","SQL Query","🗃 Data"])
            insights=""
            response_time=response['Total_time']
            if type(response['insights'])==list:
                for i,insight in enumerate(response['insights']):
                    insights+=f"{i+1}. "+insight +"\n\n"
                message= f"Response Time :: {response_time:.2f} seconds"
            else:
                insights=response['insights'] +"\n\n"
                message= f"Response Time :: {response_time:.2f} seconds"
            # Tab 1 :: Insights
            tab1.markdown(insights)
            tab1.info(message)

            # Tab 2 :: Plots
            plotly=response['plotly']
            if plotly!="":
                fig = go.Figure(data=plotly['data'], layout=plotly['layout'])
                tab2.plotly_chart(fig)
            else:
                tab2.markdown("No Plots")
            
            # Tab 3 :: SQL Query
            sql_query=response['sql_query']
            sql_explanation=response['sql_query_explanation']
            tab3.markdown(f"""```bash 
                    {sql_query}
                    """)
            # with tab3.expander("See sql query explanation.."):
            #     st.markdown(sql_explanation)
            
            # Dataframe
            if response['db_result']=="":
                data_list=""
                tab4.write("No Data")
            else:
                data_list=json.loads(response['db_result'])
                tab4.dataframe(data_list)
                

            data1={"insight":insights,
            "plot":plotly,
            "sql_query":sql_query,
            "sql_query_exp":sql_explanation,
            "df":data_list,
            "message":message,
            "flow":flow
            }
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": data1})
            st.rerun()
        

else:
    st.info("No any Database exit. Upload the New Csv File")
