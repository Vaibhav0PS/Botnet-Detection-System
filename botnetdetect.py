import sys

from detector.offline import CSV_FILENAME, TXT_FILENAME, run_offline_detection


def main():
    if len(sys.argv) < 2:
        print("Usage: python botnetdetect.py path/to/capture.pcap")
        return 1

    run_offline_detection(
        sys.argv[1],
        csv_filename=CSV_FILENAME,
        txt_filename=TXT_FILENAME,
        models_dir="Models",
        verbose=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
