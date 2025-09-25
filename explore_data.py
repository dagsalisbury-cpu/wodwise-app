# explore_data.py

import pandas as pd

# --- Configuration ---
# Make sure your CSV file is named 'crossfit_data.csv' and is in the same folder
CSV_FILE_PATH = 'crossfit_data.csv'

def explore_dataset(file_path):
    """
    Loads and provides a basic exploration of the CrossFit dataset.
    """
    try:
        # Load the dataset from the CSV file into a Pandas DataFrame
        df = pd.read_csv(file_path)
        print("✅ Dataset loaded successfully!")
        
        # --- Basic Information ---
        print("\n--- 1. First 5 Rows of Data ---")
        print(df.head()) # Shows the first few rows to give you a feel for the data

        print("\n--- 2. Dataset Info ---")
        print(df.info()) # Shows column names, data types (number, text, etc.), and non-null counts

        print("\n--- 3. Statistical Summary ---")
        # Shows stats like mean, median, min, max for numerical columns
        print(df.describe()) 
        
    except FileNotFoundError:
        print(f"❌ Error: The file '{file_path}' was not found. Please make sure it's in the right directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- Run the exploration ---
if __name__ == "__main__":
    explore_dataset(CSV_FILE_PATH)