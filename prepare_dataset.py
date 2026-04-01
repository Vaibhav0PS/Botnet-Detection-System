import pandas as pd
import glob

# read ALL csv files inside subfolders
files = glob.glob("Training_files/preprocessed_csv/**/*.csv", recursive=True)

print("Found files:", files)

df_list = []

for file in files:
    df = pd.read_csv(file)
    df_list.append(df)

dataset = pd.concat(df_list, ignore_index=True)

print("Dataset shape:", dataset.shape)

dataset.to_csv("training_dataset.csv", index=False)

print("training_dataset.csv created successfully")