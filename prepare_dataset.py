import pandas as pd
import glob
import os

# Define columns as expected by the Training_files/model.py
RAW_COLUMNS = [
    'src_ip', 'dst_ip', 'sport', 'dport', 'protocol', 
    'total_pkts', 'null_pkts', 'small_pkts', 'percent_of_sml_pkts', 
    'ratio_incoming_outgoing', 'total_duration', 'average_payload', 
    'average_payload_sent', 'average_payload_receive', 'stddev_packet_length', 
    'freq_packet_length', 'payload_per_sec', 'avg_inter_times', 
    'avg_sent_inter_times', 'avg_rec_inter_times', 'med_inter_times', 
    'med_sent_inter_times', 'med_rec_inter_times', 'var_packet_size', 
    'var_packet_size_rec', 'var_packet_size_sent', 'max_packet_size', 
    'average_packet_length', 'first_packet_length', 'average_packet_ps'
]

# read ALL csv files inside subfolders
files = glob.glob("Training_files/preprocessed_csv/**/*.csv", recursive=True)

print(f"Found {len(files)} files.")

df_list = []

for file in files:
    if file.endswith('.DS_Store'):
        continue
        
    print(f"Processing {file}...")
    # These CSVs don't have headers
    df = pd.read_csv(file, header=None, names=RAW_COLUMNS)
    
    # Add label based on path
    if 'benign' in file.lower():
        df['label'] = 0
    else:
        df['label'] = 1
        
    df_list.append(df)

if not df_list:
    print("No CSV files found to process!")
else:
    dataset = pd.concat(df_list, ignore_index=True)
    print("Dataset shape:", dataset.shape)
    dataset.to_csv("training_dataset.csv", index=False)
    print("training_dataset.csv created successfully with headers and labels.")
