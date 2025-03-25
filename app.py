import streamlit as st
from autoscraper import AutoScraper
import pandas as pd
import json
import os
from streamlit_tags import st_tags_sidebar
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the page configuration
st.set_page_config(
    page_title="AutoScraper Streamlit App",
    layout="wide",
    initial_sidebar_state="expanded",
)

# App Title
st.title("AutoScraper Interactive Web Scraper")

# Create session state variables
if 'current_scraper' not in st.session_state:
    st.session_state.current_scraper = None
if 'current_rules' not in st.session_state:
    st.session_state.current_rules = None
if 'scraping_completed' not in st.session_state:
    st.session_state.scraping_completed = False
if 'structured_result' not in st.session_state:
    st.session_state.structured_result = None

# Sidebar sections
st.sidebar.header("🔧 Scraping Configuration")

# Function to validate URL
def is_valid_url(url):
    import re
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:\S+(?::\S*)?@)?'  # user:pass@
        r'(?:'  # IP address exclusion
        r'(?P<ip>(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])'
        r'(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){3})|'
        r'(?P<domain>'
        r'(?:[a-zA-Z0-9-]+\.)+'  # Domain name
        r'[a-zA-Z]{2,}'
        r'))(?::\d{2,5})?'  # Optional port
        r'(?:/\S*)?$'
    )
    return re.match(regex, url) is not None

# Function to check scraping availability
def is_scrapable(url):
    try:
        response = requests.get(url)
        # Check if the response status code is 200 (OK)
        return response.status_code == 200
    except requests.RequestException:
        return False

# URL Input
url = st.sidebar.text_input("Enter the URL to scrape", "https://github.com/krishnaik06?tab=repositories")

# Validate URL and check scraping availability
if not is_valid_url(url):
    st.sidebar.error("Please enter a valid URL.")
elif not is_scrapable(url):
    st.sidebar.error("The URL is not accessible or scrapable.")

# Wanted List Input
st.sidebar.subheader("Example Data Points (wanted_list)")
wanted_list = st_tags_sidebar(
    label='Enter data points to scrape:',
    text='Press enter to add more',
    value=['Roadmap-To-Learn-Generative-AI-In-2024', '3,319'],
    suggestions=[],
    maxtags=-1,
    key='wanted_list',
)

# Scraping Section
st.sidebar.subheader("🚀 Run Scraper")
if st.sidebar.button("Start Scraping"):
    logging.info("Start Scraping button clicked.")
    if not is_valid_url(url):
        st.error("Invalid URL. Please enter a valid URL to proceed.")
        logging.error("Invalid URL entered.")
    elif not wanted_list:
        st.error("Please enter at least one data point in the wanted list.")
        logging.error("Wanted list is empty.")
    else:
        with st.spinner("Building scraper and scraping data..."):
            try:
                logging.info("Building scraper with URL: %s and wanted list: %s", url, wanted_list)
                scraper = AutoScraper()
                scraper.build(url, wanted_list)
                
                # Get structured results
                structured_result = scraper.get_result_similar(url, grouped=True)
                print(structured_result)
                if(structured_result == None or structured_result == {}):
                    st.error("No data found. Please check the URL and wanted list.")
                    logging.error("No data found. Please check the URL and wanted list.")
                else:
                    logging.info("Scraping completed successfully.")
                
                # Create rule aliases
                rules_dict = {}
                for i, (key, value) in enumerate(structured_result.items()):
                    alias = f"Column_{i+1}"
                    rules_dict[key] = alias
                
                # Store in session state
                st.session_state.current_scraper = scraper
                st.session_state.current_rules = rules_dict
                st.session_state.structured_result = structured_result
                st.session_state.scraping_completed = True
                
            except Exception as e:
                st.error(f"An error occurred during scraping: {e}")
                logging.error("An error occurred during scraping: %s", e)

# Separate Scraper Management Section
st.sidebar.divider()
st.sidebar.header("💾 Scraper Management")

# Save Scraper Section
save_col1, save_col2 = st.sidebar.columns([2, 1])
with save_col1:
    scraper_name = st.text_input("Scraper Name", "my-scraper")
with save_col2:
    if st.button("Save Scraper"):
        if not st.session_state.scraping_completed:
            st.sidebar.error("Please perform scraping first")
        elif not scraper_name:
            st.sidebar.error("Enter a name")
        else:
            try:
                st.session_state.current_scraper.set_rule_aliases(st.session_state.current_rules)
                st.session_state.current_scraper.save(scraper_name)
                st.sidebar.success(f"Saved as '{scraper_name}'")
            except Exception as e:
                st.sidebar.error(f"Error saving: {e}")

# Show Saved Scrapers Section
saved_scrapers = [f for f in os.listdir() if os.path.isfile(f) and 
                 not os.path.splitext(f)[1] and  # no extension
                 not f.startswith('.') and  # not hidden files
                 not f in ['LICENSE', 'README', 'Dockerfile']]  # exclude common files
if saved_scrapers:
    st.sidebar.subheader("📂 Saved Scrapers")
    
    # Create a container for saved scrapers list
    saved_list = st.sidebar.container()
    with saved_list:
        for scraper in saved_scrapers:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(scraper)
            with col2:
                if st.button("🗑️", key=f"delete_{scraper}"):
                    try:
                        os.remove(scraper)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting {scraper}: {e}")
    
    st.sidebar.divider()

# Display Results Section
if st.session_state.scraping_completed and st.session_state.structured_result:
    st.header("📊 Structured Results")
    
    # Display structured results
    with st.expander("📊 JSON RAW Results", expanded=False):
        for key, value in st.session_state.structured_result.items():
            st.markdown(f"**{key}:**")
            st.write(value)
    
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.structured_result)
    st.dataframe(df)
    
    # Download Section
    st.subheader("💾 Download Scraped Data")
    csv = df.to_csv(index=False).encode('utf-8')
    json_data = df.to_json(orient='records', lines=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name='scraped_data.csv',
            mime='text/csv',
        )
    with col2:
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name='scraped_data.json',
            mime='application/json',
        )

# Footer
st.markdown("---")
st.markdown("Developed with ❤️ using [Streamlit](https://streamlit.io/) and [AutoScraper](https://github.com/alirezamika/autoscraper).")
