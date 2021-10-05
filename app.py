import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account
import matplotlib.pyplot as plt
import pandas as pd
from urllib.request import Request, urlopen
from io import StringIO, BytesIO
import os
import json


def read_from_bucket(bucket):

    """
    This concatenates all csv files in a bucket together.
    Returns a single dataframe.
    """
    
    frames = []
    files  = list(bucket.list_blobs())
    for file in files:
        blob = bucket.blob(file.name)
        data = pd.read_csv(BytesIO(blob.download_as_string()), encoding='utf-8')
        frames.append(data)
    data = pd.concat(frames)
    return data


def return_politician_handles(option='list'):
    req = Request('https://www.politics-social.com/api/list/csv/followers', headers={'User-Agent': 'Mozilla/5.0'})
    webpage = urlopen(req).read()
    s=str(webpage,'utf-8')
    data = StringIO(s) 
    df=pd.read_csv(data)
    df['Name'] = df['Name'].apply(lambda x: x.rstrip())
    df['Screen name'] = df['Screen name'].apply(lambda x: x[1:])
    politician_handles = df['Screen name']
    print('Politician twitter handles imported.\n')

    if option=='list':
        return politician_handles
    else:
        return df


# read_from_bucket = st.cache(read_from_bucket)
return_politician_handles =  st.cache(return_politician_handles)

credentials_raw = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
service_account_info = json.loads(credentials_raw)
credentials = service_account.Credentials.from_service_account_info(
    service_account_info)

bucket_name = 'uk-gov-tweets-14289'
storage_client = storage.Client(credentials=credentials)#.from_service_account_json('/Users/mdunford/data_science/ticker-twitter/data_collection/creds.json')
bucket = storage_client.get_bucket(bucket_name)

data = read_from_bucket(bucket=bucket)
data.drop('id', axis=1, inplace=True)
data['user'] = data['user'].astype(str)

politicians = return_politician_handles(option='all')
print(politicians.sort_values(by='Screen name').head())

data = data.merge(politicians[['Name','Screen name']], how='left', left_on='user', right_on='Screen name')
print(data.sort_values(by='user').head())


# Title
st.title('UK Politics Twitter Dashboard')

# sidebar selections
party = st.sidebar.selectbox(
    'Choose political party:',
    politicians['Party'].unique()
)

selected_user = st.sidebar.selectbox(
    'Filter politician:',
    politicians[politicians['Party']==party]['Name'].unique()
)


# Bar chart of followers
st.header('Twitter followers by Party')
df = politicians.groupby('Party').sum()['Followers'].reset_index()
df = df.sort_values(by='Followers', ascending=True)
f, ax = plt.subplots()
ax.barh(y=df['Party'], width=df['Followers'])
st.pyplot(f)



# Selected user details
st.header('Tweets of chosen politician')
followers = int(politicians[politicians['Name']==selected_user]['Followers'])
change = int(politicians[politicians['Name']==selected_user]['New followers in last 24 hours'])
st.write("Selected politician: "+selected_user)
with st.container():
    st.metric(label="Followers 24hr change", value=followers, delta=change)
    st.table(data[data['Name']==selected_user][['text','created']])
