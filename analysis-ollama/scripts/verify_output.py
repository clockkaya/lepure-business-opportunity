import pandas as pd

output_file = r"F:\PROJECTS\lepure-business-opportunity\analysis-ollama\Jan_Mar_2026_CGT_Opportunities_Formatted.xlsx"

try:
    df = pd.read_excel(output_file)
    print("Columns in the formatted file:")
    print(df.columns.tolist())
    print("\nFirst 2 rows (subset of columns for brevity):")
    cols_to_show = ["相关企业", "所在省份", "所在城市", "价值摘要", "新闻原文", "发布时间"]
    print(df[cols_to_show].head(2).to_dict(orient='records'))
except Exception as e:
    print(f"Error: {e}")
