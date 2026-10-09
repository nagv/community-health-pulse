from pathlib import Path

from backend.data import sample_csv

if __name__ == "__main__":
    path = Path(__file__).with_name("synthetic_visits.csv")
    path.write_bytes(sample_csv())
    print(f"Generated {path.name} from seed 42.")
