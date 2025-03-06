import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import random
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

species = ["Adelie", "Chinstrap", "Gentoo"]

conn = st.connection("gsheets", type=GSheetsConnection)

if 'chart_displayed' not in st.session_state:
    st.session_state.chart_displayed = False
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'chart_type' not in st.session_state:
    st.session_state.chart_type = None

@st.cache_data
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
    valid_species = ["Adelie", "Chinstrap", "Gentoo"]
    invalid_rows = df[~df['species'].isin(valid_species)]
    if not invalid_rows.empty:
        st.warning(f"Found {len(invalid_rows)} rows with invalid species. They will be excluded.")
    df = df[df['species'].isin(valid_species)]
    return df

# violin  plot
def create_violin_plot(df):
    df_melted = pd.melt(
        df,
        id_vars=['species'],
        value_vars=['bill_length_mm', 'bill_depth_mm'],
        var_name='measurement',
        value_name='value'
    )
    fig = px.violin(
        df_melted,
        x='species',
        y='value',
        color='measurement',
        box=True
    )
    fig.update_traces(meanline=dict(visible=True))
    fig.update_layout(title_text='Violin Plot: Bill Length and Depth by Species')
    return fig

# pair plot (scatter matrix)
def create_pair_plot(df):
    fig = px.scatter_matrix(df, dimensions=['bill_length_mm', 'bill_depth_mm'], color='species',
                            title='Pair Plot: Bill Length vs. Bill Depth by Species')
    return fig

def main():
    st.title("Penguin Species Identification A/B Test")
    st.markdown(
        "**Question:** Can we identify a penguin species from bill length, bill depth, or a combination of both?"
    )
    df = load_data()

    if st.button("Show Chart"):
        st.session_state.chart_displayed = True
        st.session_state.start_time = time.time()
        st.session_state.chart_type = random.choice(['violin', 'pair'])

    # Display the chart and answer button if a chart is shown
    if st.session_state.chart_displayed:
        if st.session_state.chart_type == 'violin':
            fig = create_violin_plot(df)
            st.plotly_chart(fig)
        elif st.session_state.chart_type == 'pair':
            fig = create_pair_plot(df)
            st.plotly_chart(fig)

        # Button to indicate the user has answered
        if st.button("I answered your question"):
            end_time = time.time()
            duration = end_time - st.session_state.start_time
            st.success(f"Time taken to answer: {duration:.2f} seconds")
            st.balloons()
            # Reset session state for the next round
            st.session_state.chart_displayed = False
            st.session_state.start_time = None
            st.session_state.chart_type = None

if __name__ == "__main__":
    main()