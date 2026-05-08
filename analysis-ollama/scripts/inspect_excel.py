import pandas as pd

file_path = r"F:\PROJECTS\lepure-business-opportunity\analysis-ollama\Jan_Mar_2026_CGT_Opportunities.xlsx"

try:
    df = pd.read_excel(file_path)
    print("Columns in the Excel file:")
    print(df.columns.tolist())
    print("\nFirst 2 rows:")
    # Print in a way that shows more info
    print(df.head(2).to_dict(orient='records'))
except Exception as e:
    print(f"Error: {e}")
