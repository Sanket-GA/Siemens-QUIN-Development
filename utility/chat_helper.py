import os
import sqlite3
import pandas as pd
import json
import ast
from dotenv import load_dotenv
import re
import shutil
import streamlit as st
from utility.logs import *
from utility.api_calls import *
import time


load_dotenv()

class DataDictionaryPrompt():

    def __init__(self,) -> None:
        # self.file_path=st.secrets.file.file_path or os.getenv('file_path')
        # self.sheet_name=st.secrets.file.sheet_name or os.getenv('sheet_name')
        self.dict_file_path=st.secrets.file.dict_file_path or os.getenv('dict_file_path')
        self.dict_sheet_name=st.secrets.file.dict_sheet_name or os.getenv("dict_sheet_name")
        

    def __get_data_dict(self):
        try:
            # Load the Excel sheet into a pandas DataFrame
            df = pd.read_excel(self.dict_file_path, sheet_name=self.dict_sheet_name)

            # Create an in-memory SQLite database
            # conn = sqlite3.connect(":memory:")
            conn = sqlite3.connect("database.db")

            # Load the DataFrame into the SQLite database
            df.to_sql("dict_data", conn, index=False, if_exists="replace")
            
            query="select * from dict_data"

            # Execute the SQL query
            df1 = pd.read_sql_query(query, conn)
            data_dict=df1.to_dict(orient="records")
            return data_dict  # Return the DataFrame with query results
            
        except Exception as e:
            print("SQL query didn't work due to:", e)
            return None
        finally:
            # Close the database connection
            conn.close()

    def __get_top3(self):
        try:
            # Load an SQLite database
            conn = sqlite3.connect("database.db")
            
            query="""select * from sales_table limit 3"""

            # Execute the SQL query
            top_df = pd.read_sql_query(query, conn)

            return top_df  # Return the DataFrame with query results

        except Exception as e:
            print("Data Dictionary Prompt :: SQL query didn't work due to:", e)
            return None
        finally:
            # Close the database connection
            conn.close()

    def __get_table_details_with_columns(self):
        column_details=self.__get_data_dict()
        top_3=self.__get_top3()
        # Initialize a structure to hold the combined result
        result = []
        table_id = "1"
        table_name="sales_table"
        table_desc = """The table tracks sales opportunities, including campaign details, opportunity types, owners, global business units (GBU), and partner information. It captures key sales process attributes such as opportunity name, product, account segmentation, and deal registration. It also includes financial data like converted opportunity values and HPE sub-total values in different currencies. Use 'Close_Date' to track expected close dates and 'Won_Lost_Date' for sales outcomes, while 'Value_Converted' and 'HPE_Sub_Total_Converted' help assess financial performance."""
        print("Table Name ::", table_name ,"ID ::",table_id)
        # Append the table details and its columns to the result
        result.append({
            "table_id": table_id,
            "table_name":table_name,
            "table_desc": table_desc,
            "top-3":top_3.to_csv(index=False),
            "columns": [
                {
                    "col_id": column["col_id"],
                    "col_name": column["Column Name"],
                    "col_type": column['Data Type'],
                    "col_desc": column["Description"]
                }
                for column in column_details
            ]
        })
        
        return json.dumps(result)

    def get_prompt(self):
        data_dictionary=self.__get_table_details_with_columns()
        data_dictionary_prompt = ''
        for table in json.loads(data_dictionary):
            data_dictionary_prompt += f"Table Name:{table['table_name']}\nTable Description:{table['table_desc']}"
            data_dictionary_prompt += "\nColumns(with data type and description):\n"
            for column in table['columns']:
                data_dictionary_prompt += f"{column['col_name']} ({column['col_type']}) : {column['col_desc']}\n"
            data_dictionary_prompt += f"""\n/* \n3 rows from {table['table_name']} table:\n"""
            data_dictionary_prompt+=table['top-3']
            data_dictionary_prompt += "*/ \n\n"
        return data_dictionary_prompt


def extract_plotly_components(js_code):
    """
    Extracts Plotly trace and layout components from a given JavaScript code snippet.

    This function parses JavaScript code to extract Plotly `trace` and `layout` objects, 
    which are typically used to define a Plotly chart. It converts these components into 
    Python dictionaries for further use.

    Args:
        js_code (str): A string containing JavaScript code that defines Plotly charts, 
                       including `trace` and `layout` objects.

    Returns:
        dict: A dictionary with the following keys:
            - `"data"`: A list of dictionaries representing the extracted `trace` objects.
            - `"layout"`: A dictionary representing the extracted `layout` object, or 
                          `None` if no layout is found.

    Raises:
        None: Errors during JSON parsing are caught and logged, but they do not interrupt 
              the execution.

    Example:
        js_code = '''
        ```javascript
        var trace1 = {
            x: [1, 2, 3],
            y: [10, 15, 13],
            type: 'scatter'
        };

        var layout = {
            title: 'Sample Plot',
            xaxis: { title: 'X-Axis' },
            yaxis: { title: 'Y-Axis' }
        };
        ```
        '''
        components = extract_plotly_components(js_code)
        print(components)
        # Output:
        # {
        #     "data": [
        #         {"x": [1, 2, 3], "y": [10, 15, 13], "type": "scatter"}
        #     ],
        #     "layout": {
        #         "title": "Sample Plot",
        #         "xaxis": {"title": "X-Axis"},
        #         "yaxis": {"title": "Y-Axis"}
        #     }
        # }

    Notes:
        - The input JavaScript code can include multiple `trace` objects and one `layout` object.
        - The function attempts to convert JavaScript-like syntax into valid JSON before parsing.
        - Any errors encountered during JSON parsing are logged for debugging.
    """
    
    def js_to_json(js_object):
        js_object = js_object.replace("'", '"""')
        js_object = re.sub(r'(\b[a-zA-Z_][a-zA-Z0-9_]*\b):', r'"\1":', js_object)
        return js_object

    
    clean_text = js_code.replace("```javascript", "").replace("```", "").replace("`", "")

    # Extract all trace objects
    trace_matches = re.findall(r"var\s+trace\d+\s*=\s*({[\s\S]*?});", clean_text)
    traces = []
    for trace_str in trace_matches:
        try:
            trace_json = js_to_json(trace_str)  # Convert to valid JSON
#             trace_obj = json.loads(trace_json)  # Parse JSON
            trace_obj=eval(trace_json)
            traces.append(trace_obj)
        except json.JSONDecodeError as e:
            print(f"Error decoding trace: {e}")
#             print(f"Offending string:\n{trace_str}")
    
    # Extract layout object
    layout_match = re.search(r"var\s+layout\s*=\s*({[\s\S]*?});", clean_text)
    layout = None
    if layout_match:
        try:
            layout_str = layout_match.group(1)
            layout_str=layout_str.replace("false","False").replace("true","True")
            layout_json = js_to_json(layout_str)  # Convert to valid JSON
#             layout = json.loads(layout_json)  # Parse JSON
            layout=eval(layout_json)
        except json.JSONDecodeError as e:
            print(f"Error decoding layout: {e}")
            print(f"Offending string:\n{layout_str}")

    # Return extracted components
    return {
        "data": traces,
        "layout": layout}


def delete_cache_folder(dir_name = ".cache"):
    """
    Deletes a folder named '.cache' in the current working directory, if it exists.

    This function checks if a directory named '.cache' exists in the current 
    working directory. If found, it deletes the folder along with all its 
    contents. If the folder does not exist, a message is printed indicating that.

    Note:
        - Ensure you have the necessary permissions to delete the folder.
        - Deleting the '.cache' folder may remove important cached data 
          required by certain applications.

    Raises:
        OSError: If an error occurs while attempting to delete the folder.

    Example:
        delete_Cach_folder()
    """  
    # # Get the current working directory
    current_dir = os.getcwd()
    
    # # Construct the full path to the directory
    dir_path = os.path.join(current_dir, dir_name)
    
    # # Check if the directory exists
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        # Remove the directory and its contents
        shutil.rmtree(dir_path)
        print(f"The directory '{dir_name}' has been deleted.")
    else:
        print(f"The directory '{dir_name}' does not exist.")
        
        
def capitalize_sentences(text):
    """
    Capitalizes the first letter of each sentence in a text while preserving newlines.

    This function processes text by splitting it into lines, then splitting each line
    into sentences based on sentence delimiters like `.`, `!`, and `?`. The first letter
    of each sentence is capitalized, and the original newline structure is retained.

    Args:
        paragraph (str|list): The input paragraph containing sentences and newlines.

    Returns:
        str: The processed paragraph with the first letter of each sentence capitalized,
             while keeping the newline structure intact.

    Example:
        >>> paragraph = "this is the first sentence. here is the second!\n"
                        "is this the third? yes, it is.\n"
                        "another line with text. and yet another sentence."
        >>> result = capitalize_sentences_with_newlines(paragraph)
        >>> print(result)
        This is the first sentence. Here is the second!
        Is this the third? Yes, it is.
        Another line with text. And yet another sentence.
    """
    import re

    # Split the text into lines
    if type(text)==str:
        lines = text.split("\n") 
    else:
        lines=text

    capitalized_lines = []
    for line in lines:
        line=line.strip()
        # Split the line into sentences using '. ', '? ', '! ' as delimiters
        sentences = re.split(r'(?<=[.!?-])\s+', line)
        
        # Capitalize the first letter of each sentence
        capitalized_sentences = [sentence.capitalize() for sentence in sentences]
        
        # Join the sentences back into a single line
        capitalized_lines.append(' '.join(capitalized_sentences))
    
    # Join lines back with newlines
    if type(text)==str:
        capitalized_lines="\n".join(capitalized_lines)

    return capitalized_lines


def get_agent_chat_summary(response, 
                            usage,
                            logging_session_id,
                            user_question): # async
    """
    Process and summarize the agent's response for a given user query.

    This function extracts insights, SQL queries, database results, and visualizations 
    from an agent's response. It handles token usage logging, error handling, 
    and conditional processing based on the agent's output and dataset size limits.

    Parameters:
        response (dict): The agent's response, containing:
            - chat_history (list): A list of messages exchanged with the agent.
            - sql_execution_reponse (dict): Details about SQL execution and dataset size.
        usage (dict): A dictionary to track token usage (prompt and completion tokens).
        logging_session_id (str): Identifier for the logging session to retrieve chat history.
        jwt_token (str): Authentication token for accessing and updating user session history.
        user_question (str): The user's query.

    Returns:
        dict: A dictionary summarizing the processed response, including:
            - question (str): The original user query.
            - sql_query (str): The generated SQL query.
            - sql_query_explanation (str): Explanation of the SQL query.
            - insights (str): Extracted insights or summary.
            - db_result (str): Result of the database query (if applicable).
            - usage (dict): Updated token usage details.
            - plotly (any): Extracted Plotly visualization components (if applicable).
            - response_flag (int): Status indicator (0: no results, 1: valid results).

    Notes:
        - Handles cases where the dataset size is too large, too small, or empty.
        - Logs token usage and clears temporary session history after processing.
        - If Python code for visualizations exists in the chat history, it extracts and processes it.

    Example:
        result = get_agent_chat_summary(response, usage, session_id, token, "What is the sales trend?")
        print(result["insights"])  # Outputs the insights derived from the agent's response.
    """

    # Initialize variables for SQL query, insights, and database results
    sql_query = ''
    insights = ''
    db_result = None
    
    ## Step-1 :: Extract chat history and SQL execution response from the agent's response
    try:
        chat_history = response['chat_history']
        sql_execution_response = response['sql_execution_response']
        message= response['message']
        
    except Exception as e:
        print("Step-1 :: Error executing chat history and sql_execution_response ::",e)
    
   ## Step-2 :: # Retrieve and calculate token usage from the logging session
    if message== 'ok':
        try:
            log_df,log_status=log_processing(logging_session_id)
            # Grouping by 'source_name' and calculating the count and sum
            if log_status==1:
                print("------------Agent Token Count-----------")
                # log_data = log_df.groupby("source_name").agg(
                #         count=("source_name", "count"),
                #         completion_tokens_sum=("completion_tokens", "sum"),
                #         prompt_tokens_sum=("prompt_tokens", "sum"),
                #         response_time_sum=("response_time","sum")
                #     ).reset_index()
                usage['prompt_tokens']+=int(log_df['prompt_tokens'].sum())
                usage['completion_tokens']+=int(log_df['completion_tokens'].sum())
                # total_tokens=int(log_df['total_tokens'].sum())
                print("usage ::",usage)
            else:
                print("No Logs available for this question...")
        except Exception as e:
            print("Step-2 :: Error executing Retrieve and calculate token usage from the logging session ::",e)
     

        # Extract relevant chat history segments for SQL and insights generation
        insights_generator_lst = [x['content'] for x in chat_history if x.get('name') == 'insights_generator']
        sql_query_executor_lst = [x['content'] for x in chat_history if x.get('name') == 'sql_query_executor']
        # sql_critic_lst = [x['content'] for x in chat_history if x.get('name') == 'sql_critic']

        #step-4 ::If insights are available, process them
        if len(insights_generator_lst) > 0:
            # Remove any extra text like "TERMINATE-AGENT" at the end of the response
            content = insights_generator_lst[0].split("TERMINATE-AGENT")[0].strip()
            
            print("------------CONTENT")
            print(content)
            try:
                temp = json.loads(content)
                insights = temp.get('insights')
                sql_query = temp.get('generated_sql_query')
                ploty_code = temp.get('plotly_code')
                plotly_data=extract_plotly_components(ploty_code) 
                response_flag=1
                print("-----------------------Plotly--------------------")
                print(plotly_data)
                print("------------------------insights------------------------")
                print(insights)
            except json.JSONDecodeError as e:
                print(f"Error Decoding Insights Generator JSON: {e}")

        # step-5 :: Handle cases where the agent terminates the flow or SQL execution fails
        try:
            if chat_history[1]['name']=="planner" and "terminate-flow" in chat_history[1]['content'].lower():
                print("---------------------Planner Terminated---------------------------")
                st.session_state.history_manager.append({"role":"user","content":user_question})
                insights=chat_history[1]['content'].lower().split("terminate-flow:")[-1]
                st.session_state.history_manager.append({"role":"assistent","content":insights})
                print("Chat history stored successfully.")
                plotly_data=""
                sql_query=""
                response_flag=0 # No Valid Results
            # if agent stop without running the sql_excutor agent then process 
            elif len(sql_query_executor_lst)==0:
                    sql_query=""
                    insights="Sorry, I wasn't able to generate the correct query. Would you like to rephrase the question?"
                    plotly_data=""
                    response_flag=0 # No Valid Results
        except Exception as e:
            print("Step-5 :: Handle cases where the agent terminates the flow or SQL execution fails ::",e)
        
        # Handle cases based on dataset size flags
        #step-6 ::sql executor agent return dataset size is > 20
        try:
            if sql_execution_response['data_size_flag'] == 'exceeding-limit':
                print("------------Exceeding limit------------")
                sql_query = sql_execution_response['generated_sql_query']
                insights = 'Due to large dataset the insights could not be generated. You can download the resultset from the Data Tab'
                plotly_data=""
                response_flag=1 # Valid Results

            # sql executor agent return dataset size is ==0.
            elif sql_execution_response['data_size_flag'] == 'zero-limit':
                print("------------Zero limit------------")
                sql_query = sql_execution_response['generated_sql_query']
                insights =  "Sorry, I wasn't able to generate the correct query. Would you like to rephrase the question?"
                plotly_data=""
                response_flag=1 # Valid Results

            # sql executor agent return dataset size is == 1.
            elif sql_execution_response['data_size_flag'] == 'one-limit':
                # print(sql_execution_response)
                print("------------One limit------------")
                sql_query = sql_execution_response['generated_sql_query']
                data = sql_execution_response['df']
                question=sql_execution_response['user_question']
                plotly_data=""
                prompt_=f"""You are an insights generator. When provided with a user's question and corresponding data as the answer, deliver a concise response in 1 to 4 lines. Your response must directly reference the provided data to address the question accurately, without performing any additional calculations or extrapolations.
                question:{question}
                data:{data}
                response:(textual response)"""
                insights,insights_usage=one_limit_call(prompt_)
                # Update token usage: one limit open ai
                usage['prompt_tokens']+=insights_usage['prompt_tokens']
                usage['completion_tokens']+=insights_usage['completion_tokens']
                print("One Limit Insights Token Count Added")
                print("usage ::",usage)
                response_flag=1 # Valid Results
        
        except Exception as e:
                print("Error executing prompt tokens ::",e)

        # Explain the SQL query if available
        if sql_query!="":
            # clear the temp session history once get the complete response of user question
            st.session_state.history_manager=[]
            query_explanation,sql_usage =sql_explanation(sql_query)
            df=sql_execution_response['df']
            # Update token usage: sql explanation
            usage['prompt_tokens']+=sql_usage['prompt_tokens']
            usage['completion_tokens']+=sql_usage['completion_tokens']
            print("--------SQL query explanation Token Count Added")
            print("usage ::",usage)
            print("--------------------SQL Query---------------------")
            print(sql_query)
            print("--------------------Query Explanation---------------------")
            print(query_explanation)
        else:
            query_explanation=""
            df=""
        
        print("prompt_tokens ::",usage['prompt_tokens'])
        print("completion_tokens ::",usage['completion_tokens'])
        print("---Usage--")
        print("TOTAL: ", usage)

        
        ## delete the autogen .cache memory
        delete_cache_folder()
        clear_logs(logging_session_id)
        return {"question":user_question,
            "sql_query": sql_query,
            "sql_query_explanation": query_explanation,
            "insights": capitalize_sentences(insights),
            "db_result": df,
            "usage": usage,
            "plotly":plotly_data,
            "response_flag":response_flag
            }
    else :
        delete_cache_folder()
        clear_logs(logging_session_id)
        response_flag=0
        return {"question":user_question,
            "sql_query": '',
            "sql_query_explanation": '',
            "insights": capitalize_sentences(message),
            "db_result": '',
            "usage": usage,
            "plotly":'',
            "response_flag":response_flag
            }

def data_processing(df):
    pre_start=time.time()
    # Rename the column name
    df.rename(columns={
    "Created Date":"Created_Date",
    "Primary Campaign Source": "Primary_Campaign_Source",
    "Country": "Country",
    "Opportunity Owner": "Opportunity_Owner",
    "User Role Type": "User_Role_Type",
    "GBU": "GBU",
    "Opportunity Type": "Opportunity_Type",
    "HPE Opportunity Id": "HPE_Opportunity_Id",
    "Unique": "Unique",
    "Deal Registration Id": "Deal_Registration_Id",
    "Deal Registration Status": "Deal_Registration_Status",
    "HP Quote": "HP_Quote",
    "Quote Number": "Quote_Number",
    "Opportunity Name": "Opportunity_Name",
    "Product Name": "Product_Name",
    "Account Name Latin Capture": "Account_Name_Latin_Capture",
    "Coverage Segmentation": "Coverage_Segmentation",
    "Partner account ID": "Partner_Account_ID",
    "Primary Channel Partner": "Primary_Channel_Partner",
    "MDF Partner": "MDF_Partner",
    "Owner Role": "Owner_Role",
    "Managed By": "Managed_By",
    "Owner Company Type": "Owner_Company_Type",
    "Go To Market Route": "Go_To_Market_Route",
    "Prior Sales Stage": "Prior_Sales_Stage",
    "Sales Stage": "Sales_Stage",
    "Forecast Category": "Forecast_Category",
    "Close Date": "Close_Date",
    "Won/Lost Date": "Won_Lost_Date",
    "Fulfillment": "Fulfillment",
    "Customer Engagement": "Customer_Engagement",
    "Value (converted) Currency": "Value_Converted_Currency",
    "Value (converted)": "Value_Converted",
    "HPE Sub Total (converted) Currency": "HPE_Sub_Total_Converted_Currency",
    "HPE Sub Total (converted)": "HPE_Sub_Total_Converted"
    }, inplace=True)

    # Drop the Rows is title missing values
    new_df=df.copy()  #.dropna(subset=['Title'])
    # Convert the Processing Date Month to the Datetime
    new_df['Won_Lost_Date']=pd.to_datetime(new_df['Won_Lost_Date'])

    # Convert the Release Date Month to the Datetime
    new_df['Won_Lost_Date']= new_df['Won_Lost_Date'].dt.date # strftime('%Y-%m-%d') # YYYY-MM-DD
   
    text_columns =  ["primary_campaign_source", "country","opportunity_owner","user_role_type","gbu","opportunity_type",
    "hpe_opportunity_id","deal_registration_id","deal_registration_status", "hp_quote","quote_number", "opportunity_name",
    "product_name", "account_name_latin_capture","coverage_segmentation","partner_account_id", "primary_channel_partner",
    "mdf_partner","owner_role","managed_by", "owner_company_type", "go_to_market_route", "prior_sales_stage","sales_stage",
    "forecast_category", "fulfillment", "customer_engagement", "currency","hpe_sub_total_converted_currency"]
    date_columns = ["created_date", "close_date", "won_lost_date"]
    numeric_columns = ["Unique", "Value_Converted", "HPE_Sub_Total_Converted"]

    for col in numeric_columns:
        if df[col].dtypes=="O":
            new_df[col]=new_df[col].apply(lambda row: row.replace(",",""))
        new_df[col]=new_df[col].astype('int')
    
    # Load the Csv sheet data into SQL Lite
    print("-------------------------Column Names--------------------------")
    print(new_df.columns)
    print("Size of Data ::",new_df.shape[0])
    print("-------------------------------------------------------------")
    new_df.to_csv("process_data.csv")

    # Create an in-memory SQLite database
    # conn = sqlite3.connect(":memory:")
    conn = sqlite3.connect("database.db")
    # Load the DataFrame into the SQLite database
    new_df.to_sql("sales_table", conn, index=False, if_exists="replace")
    st.success("File has been saved in local Database.")
    pre_end=time.time()
    print("Data Processing and Loading Time::",pre_end-pre_start)



    

