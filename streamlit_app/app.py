import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import boto3

ddb = boto3.resource('dynamodb')
dynamodb = boto3.client('dynamodb')

def fetch_prompts():
    prompt_table = ddb.Table('bedrockbenchmarkprompts')

    prompts = prompt_table.scan()

    df = pd.json_normalize(prompts['Items'])

    return df

def fetch_data():
    
    table = ddb.Table('bedrockbenchmark')

    response = table.scan()

    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey']
            )
    data.extend(response['Items'])
    
    df = pd.json_normalize(response['Items'])

    if 'Rating' in df.columns:
        df1 = df.drop(columns=['output_hash', 'output_token_count', 'input_token_count', 'prompt_model_id', 'Rating'])
    else:
        df1 = df.drop(columns=['output_hash', 'output_token_count', 'input_token_count', 'prompt_model_id'])

    df2 = df['model_prompt_id'].str.split('_', n=1, expand=True)
    df2.columns = ['model','prompt']
    
    df3 = pd.concat([df1,df2], axis=1)

    df4 = df3.copy()
    
    df4 = df4.drop_duplicates(subset=['date', 'model', 'prompt']).reset_index(drop=True)

    df4['date']= pd.to_datetime(df4['date'])
    
    
    # get the latest record per model/prompt category
    latest_records = df4.sort_values(by=['date'], ascending=False).groupby(['model','prompt']).nth(0)
    latest_records.reset_index(inplace=True)
    latest_records = latest_records.sort_values(by=['prompt', 'model'])
    latest_records['output'] = latest_records['output'].str.replace('\n', ' ')

    unique_values = latest_records['model_prompt_id'].values
    
    # get the prior record per model/prompt category
    latest_records_1 = df4.sort_values(by=['date'], ascending=False).groupby(['model','prompt']).nth(1)
    latest_records_1.reset_index(inplace=True)

    # only for the records in the latest dataframe (above)
    latest_records_1 = latest_records_1[latest_records_1['model_prompt_id'].isin(unique_values)]

    latest_records_1 = latest_records_1.sort_values(by=['prompt', 'model'])
    latest_records_1['output'] = latest_records_1['output'].str.replace('\n', ' ')
    
    result = pd.merge(latest_records, latest_records_1[['prompt','model','date','output']], on=["model","prompt"])
    result.drop(columns=['model_config', 'model_prompt_id'], inplace=True)
    
    return result


def put_item(key, new_attributes):
    table_name = 'bedrockbenchmark'
    dynamodb.update_item(
        TableName=table_name,
        Key=key,
        AttributeUpdates={
            attribute_name: {
                'Action': 'PUT',  # Use 'PUT' to add or update attributes
                'Value': attribute_value
            }
            for attribute_name, attribute_value in new_attributes.items()
        }
    )

#@st.cache_data
def load_csv(file_path):
    df = pd.read_csv(file_path)
    return df

# Creating the Layout of the App
st.set_page_config(layout="wide")

st.write("<div style='text-align: center; padding: 20px; font-size: 24px;'>LLM Human-In-The-Loop Dashboard</div>", unsafe_allow_html=True)

# columns
col1, col2, col3 = st.columns(3)
# rows
row1, row2 = st.columns(2)

col4, col5, col6 = st.columns(3)


# Main Streamlit app
def main():
    
    # Get or initialize session state for row index
    if 'row_index' not in st.session_state:
        st.session_state.row_index = 0 # Initialize row_index as 0
    
    # Get or initialize session state for user entries
    if 'new_values' not in st.session_state:
        st.session_state.new_values = []  # Initialize new_values as an empty list
        
    prompts = fetch_prompts()
    
    df = fetch_data()
    

    # add rating column to store user feedback
    df['rating'] = ''
    # go through the rows in the csv file and display them one by one

    if len(df) == 0:
        st.write("No data from the prior run exist yet for comparison.")

    else:
        with col6:        
            if st.button("Next"):
                if st.session_state.row_index < len(df) - 1:
                    st.session_state.row_index += 1
                else:
                    st.warning("No more rows to display.")
                    df['rating'] = st.session_state.new_values
                    #df.to_csv('my_df.csv',index=False)
                    
                    for i in range(len(df)): 
                        key = {
                            'model_prompt_id': {'S': df.loc[i,'model'] + '_' +df.loc[i,'prompt']},
                            'Date': {'S': str(df.loc[i,'Date_x']).split()[0]}
                        }

                        # Create a dictionary with the new attribute(s) to add
                        new_attributes = {
                            'Rating': {'N': str(df.loc[i,'rating'])}
                        }
                        put_item(key, new_attributes)
                        
                    st.success(f"DataFrame saved")

                    return
        
        # Display old and new responsess
        st.write("model: ", df.iloc[st.session_state.row_index, 0])
        st.write(f"{st.session_state.row_index+1} out of {len(df)}")
        

        col1.markdown(prompts[prompts.id == df.iloc[st.session_state.row_index, 1] ]['prompt'].values[0], unsafe_allow_html=True)

        with col2:
            row1.header("latest response")
            row1.markdown(df.loc[st.session_state.row_index, "output_x"], unsafe_allow_html=True)

            row2.header("previous response")
            if (df.date_x != df.date_y).all():
                row2.markdown(df.iloc[st.session_state.row_index, df.columns.get_loc("output_y")], unsafe_allow_html=True)
            else:
                row2.markdown("no prior evaluation exist yet", unsafe_allow_html=True)
            
            
        # collect teh user feedback
        with col4:
            new_value = st.selectbox(f"**Choose 0 if 'INCORRECT', 1 if 'CORRECT' and 2 if 'EXCELLENT'**", [0, 1, 2], key=st.session_state.row_index)

            
        # remove duplicated entries due to the default value in the user entry
        if new_value is not None:
            if len(st.session_state.new_values) > st.session_state.row_index:
                st.session_state.new_values[st.session_state.row_index] = new_value
            else:
                st.session_state.new_values.append(new_value)

if __name__ == '__main__':
    main()
