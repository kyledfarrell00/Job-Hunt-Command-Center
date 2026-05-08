import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB_NAME = 'job_hunt_command_center.db'


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            location TEXT,
            status TEXT,
            score REAL,
            recommendation TEXT,
            notes TEXT,
            created_date TEXT
        )
    ''')
    conn.commit()
    conn.close()


def add_job(company, title, location, status, score, recommendation, notes):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO jobs (company, title, location, status, score, recommendation, notes, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (company, title, location, status, score, recommendation, notes, str(date.today()))
    )
    conn.commit()
    conn.close()


def load_jobs():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT * FROM jobs ORDER BY id DESC', conn)
    conn.close()
    return df


st.set_page_config(page_title='Job Hunt Command Center', layout='wide')

init_db()

st.title('Job Hunt Command Center')

st.header('Add Job Opportunity')

with st.form('job_form'):
    company = st.text_input('Company')
    title = st.text_input('Job Title')
    location = st.text_input('Location')
    status = st.selectbox('Application Status', ['Found', 'Applied', 'Interview', 'Rejected'])

    st.subheader('Fit Scoring')
    clearance = st.slider('Clearance Fit', 0, 100, 50)
    experience = st.slider('Experience Fit', 0, 100, 50)
    domain = st.slider('Domain Fit', 0, 100, 50)
    writing = st.slider('Writing/Reporting Fit', 0, 100, 50)
    technical = st.slider('Technical Tools Fit', 0, 100, 50)
    location_fit = st.slider('Location Fit', 0, 100, 50)
    career = st.slider('Long-Term Career Fit', 0, 100, 50)

    notes = st.text_area('Notes')

    submitted = st.form_submit_button('Save Job')

    if submitted:
        score = round((clearance + experience + domain + writing + technical + location_fit + career) / 7, 1)

        if score >= 75:
            recommendation = 'Apply'
        elif score >= 55:
            recommendation = 'Borderline'
        else:
            recommendation = 'Skip'

        add_job(company, title, location, status, score, recommendation, notes)

        st.success(f'Job saved with recommendation: {recommendation} ({score})')

st.header('Dashboard')

jobs_df = load_jobs()

if not jobs_df.empty:
    col1, col2, col3 = st.columns(3)

    col1.metric('Total Jobs', len(jobs_df))
    col2.metric('Applications Submitted', len(jobs_df[jobs_df['status'] == 'Applied']))
    col3.metric('Interviews', len(jobs_df[jobs_df['status'] == 'Interview']))

    st.subheader('Tracked Jobs')
    st.dataframe(jobs_df)
else:
    st.info('No jobs added yet.')
