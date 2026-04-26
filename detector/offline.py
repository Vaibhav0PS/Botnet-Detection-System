import csv

from detector.feature_extractor import extract_feature_records_from_pcap, records_to_dataframe
from detector.host_aggregator import host_status_lines
from detector.predictor import BotnetPredictor, label_results


CSV_FILENAME = "flows_preprocessed_with_prediction.csv"
TXT_FILENAME = "result.txt"


def run_offline_detection(
    pcap_path,
    csv_filename=CSV_FILENAME,
    txt_filename=TXT_FILENAME,
    models_dir="Models",
    verbose=True,
):
    with open(csv_filename, "w+", newline="") as fp:
        csv.writer(fp)

    records, all_ips = extract_feature_records_from_pcap(pcap_path, verbose=verbose)
    raw_frame = records_to_dataframe(records)
    raw_frame.to_csv(csv_filename, header=False, index=False)

    predictor = BotnetPredictor(models_dir=models_dir)
    labels, src_ip_list, dst_ip_list, dataframe = predictor.predict_records(records)
    labelled_pred = label_results(labels)

    dataframe["src_ip"] = src_ip_list
    dataframe["dst_ip"] = dst_ip_list
    dataframe["label"] = labelled_pred
    dataframe = dataframe.reindex(sorted(dataframe.columns), axis=1)
    dataframe.to_csv(csv_filename, index=False)

    with open(txt_filename, "w", newline="") as text_file:
        for line in host_status_lines(src_ip_list.values, labels, all_ips):
            text_file.write(line + "\n")

    return dataframe
