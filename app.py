import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import random
import plotly.express as px
import pandas as pd
from datetime import datetime
import uuid
import scipy.stats as stats

st.set_page_config(
    page_title="Penguin Species Identification A/B Test",
    page_icon="🐧",
    layout="wide"
)

species = ["Adelie", "Chinstrap", "Gentoo"]

if 'chart_displayed' not in st.session_state:
    st.session_state.chart_displayed = False
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'chart_type' not in st.session_state:
    st.session_state.chart_type = None
if 'interaction_logged' not in st.session_state:
    st.session_state.interaction_logged = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_connection()

@st.cache_data(ttl=600)
def load_data():
    try:
        df = conn.read(worksheet="penguins")
        valid_species = ["Adelie", "Chinstrap", "Gentoo"]
        df['species'] = df['species'].astype(str)

        invalid_rows = df[~df['species'].isin(valid_species)]
        if not invalid_rows.empty:
            st.warning(f"Found {len(invalid_rows)} rows with invalid species. They will be excluded.")

        df = df[df['species'].isin(valid_species)]
        num_cols = ['bill_length_mm', 'bill_depth_mm']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=num_cols + ['species'])
        return df
    except Exception as e:
        st.error(f'Error loading penguin data: {str(e)}')
        return pd.DataFrame(columns=['species', 'bill_length_mm', 'bill_depth_mm'])

@st.cache_data(ttl=10)
def get_interactions_data():
    try:
        df = conn.read(worksheet="interactions")
        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'user_id', 'chart_type', 'time_taken'])
        if 'time_taken' in df.columns:
            df['time_taken'] = pd.to_numeric(df['time_taken'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error reading interaction data: {e}")
        return pd.DataFrame(columns=["timestamp", "user_id", "chart_type", "time_taken"])

def log_interaction(chart_type, time_taken):
    try:
        new_row = {
            "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": st.session_state.user_id,
            "chart_type": chart_type,
            "time_taken": time_taken
        }
        try:
            existing_data = get_interactions_data()
        except Exception:
            existing_data = pd.DataFrame(columns=['timestamp', 'user_id', 'chart_type', 'time_taken'])

        new_data = pd.DataFrame([new_row])
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)

        conn.update(worksheet="interactions", data=updated_data)
        return True

    except Exception as e:
        st.error(f'Error logging interaction log data: {e}')
        return False

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
        box=True,
        hover_data=['species', 'measurement', 'value'],
    )
    fig.update_traces(
        meanline=dict(visible=True)
    )

    fig.update_layout(
        title='Bill Length and Depth by Penguin Species',
        legend_title='Measurement',
        xaxis_title='Penguin Species',
        yaxis_title='Measurement (mm)',
    )
    return fig

# pair plot (scatter matrix)
def create_pair_plot(df):
    fig = px.scatter_matrix(
        df, dimensions=['bill_length_mm', 'bill_depth_mm'], color='species',
        labels={'bill_length_mm': 'Bill Length (mm)','bill_depth_mm': 'Bill Depth (mm)'},
        hover_data=['species']
    )

    fig.update_layout(
        title='Bill Length and Depth by Penguin Species',
    )
    return fig

def display_stats(interactions_data):
    if interactions_data.empty:
        st.info('No interactions data recorded yet.')
        return
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('#### Summary Statistics')
        st.write(f"📊 Total interactions recorded: **{len(interactions_data)}**")

        avg_by_chart = interactions_data.groupby('chart_type')['time_taken'].agg(['mean', 'count', 'min', 'max', 'std'])
        avg_by_chart = avg_by_chart.rename(columns={
            'mean': 'Average Time Taken (s)',
            'count': 'Count',
            'min': 'Minimum Time Taken (s)',
            'max': 'Maximum Time Taken (s)',
            'std': 'Standard Deviation (s)'
        })
        avg_by_chart['Average Time Taken (s)'] = avg_by_chart['Average Time Taken (s)'].round(2)
        avg_by_chart['Minimum Time Taken (s)'] = avg_by_chart['Minimum Time Taken (s)'].round(2)
        avg_by_chart['Maximum Time Taken (s)'] = avg_by_chart['Maximum Time Taken (s)'].round(2)

        st.dataframe(avg_by_chart, use_container_width=True)

    with col2:
        if len(avg_by_chart) > 0:
            fig = px.bar(
                avg_by_chart,
                y='Average Time Taken (s)',
                color=avg_by_chart.index,
                error_y=interactions_data.groupby('chart_type')['time_taken'].sem(),
                labels={'y': 'Average Time (seconds)', 'index': 'Chart Type'},
                title="Average Response Time by Chart Type",
            )
            fig.update_layout(showlegend=False, xaxis_title="Chart Type")
            st.plotly_chart(fig, use_container_width=True)


def main():
    st.title("🐧 Penguin Species Identification")
    st.markdown("""
    #### Research Question 
    'Can we identify a penguin species from bill length, bill depth, or a combination of both?'
    
    This app tests which visualization is more effective at helping users answer this question using A/B testing. 
    """
    )

    df = load_data()
    if df.empty:
        st.error('No penguin data available. Data source must be checked.')
        return

    col1, col2 = st.columns([3,1])
    with col1:
        chart_container = st.container()
        if st.session_state.chart_displayed:
            with chart_container:
                if st.session_state.chart_type == 'violin':
                    fig = create_violin_plot(df)
                    st.plotly_chart(fig, use_container_width=True)
                elif st.session_state.chart_type == 'pair':
                    fig = create_pair_plot(df)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            with chart_container:
                st.info("Click 'Start Test' to display a random chart type and begin the test.")

    with col2:
        if not st.session_state.chart_displayed:
            if st.button("Start Test", use_container_width=True):
                st.session_state.chart_displayed = True
                st.session_state.start_time = time.time()
                st.session_state.chart_type = random.choice(['violin', 'pair'])
                st.session_state.interaction_logged = False
                st.rerun()
        else:
            elapsed_time = time.time() - st.session_state.start_time
            st.markdown(f"⏱️ Time elapsed: **{elapsed_time:.1f}s**")
            st.markdown(f"📊 Chart type: **{st.session_state.chart_type}**")

            if st.button("I Can Answer Now", use_container_width=True):
                end_time = time.time()
                duration = end_time - st.session_state.start_time
                if not st.session_state.interaction_logged:
                    success = log_interaction(st.session_state.chart_type, duration)
                    if success:
                        st.session_state.interaction_logged = True
                        st.markdown(f"""
                        🐧Interactions logged successfully! 
                        Time taken: **{duration:.2f} seconds.**
                        """)
                    else:
                        st.error('Failed to log interactions. Please try again.')
                st.session_state.interaction_logged = False
                st.session_state.chart_displayed = False
                st.session_state.chart_type = None
                st.session_state.start_time = None

                # a small delay before rerunning to show all messages
                time.sleep(3)
                st.rerun()

    st.markdown("---")
    with st.expander("📈 Test Results and Analysis", expanded=False):
        interactions_data = get_interactions_data()
        tab1, tab2 = st.tabs(['Summary Statistics', 'Raw Data'])
        with tab1:
            display_stats(interactions_data)
            if not interactions_data.empty and len(interactions_data) > 20:
                st.markdown("#### Statistical Analysis")
                try:
                    violin_times = interactions_data[interactions_data['chart_type'] == 'violin']['time_taken']
                    pair_times = interactions_data[interactions_data['chart_type'] == 'pair']['time_taken']

                    if len(violin_times) > 0 and len(pair_times) > 0:
                        t_stat, p_val = stats.ttest_ind(violin_times, pair_times, equal_var=False)
                        st.markdown(f"""
                        **T-test results:**
                        - t-statistic: {t_stat:.3f}
                        - p-value: {p_val:.3f}
                        
                        **Interpretation:**
                        {'There is a statistically significant difference between the chart types (p < 0.05).' if p_val < 0.05
                        else 'There is no statistically significant difference between the chart types (p >= 0.05).'}
                        """)
                except Exception as e:
                    st.warning(f'Could not calculate t-test statistics. Error: {e}')
            else:
                st.info('There is not enough data to perform a meaningful test.')

        with tab2:
            st.dataframe(interactions_data, use_container_width=False)
            if not interactions_data.empty:
                csv = interactions_data.to_csv(index=False)
                st.download_button(
                    label = "Download data as CSV",
                    data = csv,
                    file_name = "penguin_ab_test_interactions.csv",
                    mime='text/csv'
                )


if __name__ == "__main__":
    main()