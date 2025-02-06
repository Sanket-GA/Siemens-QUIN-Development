import streamlit as st
import pandas as pd
from PIL import Image
import re
import os
import time


# Functions
def add_logo(logo_path, width, height):
    """Load and resize a logo image."""
    try:
        logo = Image.open(logo_path)
        return logo.resize((width, height))
    except Exception as e:
        st.error(f"Error loading logo: {e}")
        return None

def add_plot(plot_path):
    """Load and return the plot image."""
    try:
        plot_path=r"D:\33. semain\Siemens-QUIN-Development\faq_streamlit_genai\plots\top_5_regions_opportunities.png"
        return Image.open(plot_path)
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Error loading plot: {e}")
        return None

def load_dataframe(file_path):
    """Load a dataframe from a CSV file."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Dataframe file not found at {file_path}.")
        return None
    except Exception as e:
        st.error(f"Error loading dataframe: {e}")
        return None