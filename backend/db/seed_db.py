import sqlite3
import pandas as pd
import json
import os
import glob as _glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "db", "pricing.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

CONVERSION_FACTOR = 33.4009


def seed_database(db_path: str | None = None):
    db_path = db_path or os.getenv("DATABASE_PATH") or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)

    # Create tables
    conn.executescript("""
        DROP TABLE IF EXISTS medicare_rates;
        DROP TABLE IF EXISTS cci_edits;
        DROP TABLE IF EXISTS state_laws;

        CREATE TABLE medicare_rates (
            cpt_code TEXT NOT NULL,
            description TEXT,
            non_facility_price REAL,
            facility_price REAL,
            status_code TEXT,
            PRIMARY KEY (cpt_code)
        );

        CREATE TABLE cci_edits (
            column1_code TEXT NOT NULL,
            column2_code TEXT NOT NULL,
            effective_date TEXT,
            deletion_date TEXT,
            modifier_indicator TEXT,
            PRIMARY KEY (column1_code, column2_code)
        );

        CREATE TABLE state_laws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_code TEXT NOT NULL,
            state_name TEXT NOT NULL,
            law_name TEXT NOT NULL,
            law_citation TEXT NOT NULL,
            category TEXT NOT NULL,
            summary TEXT NOT NULL,
            applies_to TEXT,
            effective_date TEXT,
            url TEXT
        );
    """)

    # ── Load CMS fee schedule ──
    cms_path = os.path.join(DATA_DIR, "cms_fee_schedule.csv")
    if os.path.exists(cms_path):
        # Skip first 9 rows (copyright/header), row 10 (index 9) has column names
        df = pd.read_csv(cms_path, skiprows=9, low_memory=False)

        # Normalize column names: strip whitespace
        df.columns = [c.strip() for c in df.columns]

        # The CMS file has duplicate column names that pandas disambiguates with .1 suffixes.
        # Based on the actual header layout:
        #   col 0: HCPCS, col 1: MOD, col 2: DESCRIPTION, col 3: CODE (status),
        #   col 11: TOTAL (NON-FACILITY TOTAL), col 12: TOTAL.1 (FACILITY TOTAL)
        rename = {
            "HCPCS": "cpt_code",
            "MOD": "mod",
            "DESCRIPTION": "description",
            "CODE": "status_code",
            "TOTAL": "nf_total",
            "TOTAL.1": "f_total",
        }
        df = df.rename(columns=rename)

        # Verify we got the columns we need
        required = ["cpt_code", "description", "nf_total", "f_total"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise RuntimeError(
                f"CMS fee schedule is missing required columns {missing}. "
                f"Available columns include: {list(df.columns)[:15]}"
            )
        else:
            # Filter: only rows where MOD is blank/empty (no modifier variants)
            if "mod" in df.columns:
                df = df[df["mod"].isna() | (df["mod"].astype(str).str.strip() == "")]

            # Filter: only payable status codes (A, R, T)
            if "status_code" in df.columns:
                df = df[df["status_code"].isin(["A", "R", "T"])]

            # Convert RVU totals to dollar prices using conversion factor
            df["nf_total"] = pd.to_numeric(df["nf_total"], errors="coerce")
            df["f_total"] = pd.to_numeric(df["f_total"], errors="coerce")

            # Drop rows where both totals are zero or null
            df = df[~((df["nf_total"].fillna(0) == 0) & (df["f_total"].fillna(0) == 0))]

            df["non_facility_price"] = (df["nf_total"] * CONVERSION_FACTOR).round(2)
            df["facility_price"] = (df["f_total"] * CONVERSION_FACTOR).round(2)

            # Clean up cpt_code
            df["cpt_code"] = df["cpt_code"].astype(str).str.strip()

            # Keep only needed columns, deduplicate by cpt_code (keep first)
            if "status_code" not in df.columns:
                df["status_code"] = "A"

            df_final = df[["cpt_code", "description", "non_facility_price", "facility_price", "status_code"]].copy()
            df_final = df_final.drop_duplicates(subset=["cpt_code"], keep="first")

            df_final.to_sql("medicare_rates", conn, if_exists="append", index=False)
            print(f"Loaded {len(df_final)} CPT codes from CMS fee schedule")

            # Load Clinical Lab Fee Schedule (lab codes paid separately)
            _load_clfs(conn)
    else:
        raise FileNotFoundError(
            f"CMS fee schedule not found at {cms_path}. "
            "Place the real CMS file in backend/data/ before seeding."
        )

    # ── Load CCI edits ──
    # Try xlsx first (CMS distributes as Excel), then csv
    cci_xlsx = os.path.join(DATA_DIR, "cci_edits.xlsx")
    cci_csv = os.path.join(DATA_DIR, "cci_edits.csv")
    if os.path.exists(cci_xlsx) or os.path.exists(cci_csv):
        if os.path.exists(cci_xlsx):
            # The xlsx has 5 header/legend rows before data starts at row 5
            cci = pd.read_excel(cci_xlsx, skiprows=5, header=None,
                                names=["column1_code", "column2_code", "_existence",
                                       "effective_date", "deletion_date", "modifier_indicator", "_rationale"])
        else:
            cci = pd.read_csv(cci_csv)

        # Keep only the columns we need
        keep_cols = ["column1_code", "column2_code", "effective_date", "deletion_date", "modifier_indicator"]
        cci = cci[[c for c in keep_cols if c in cci.columns]].copy()

        # Clean codes: convert to string, strip whitespace
        cci["column1_code"] = cci["column1_code"].astype(str).str.strip()
        cci["column2_code"] = cci["column2_code"].astype(str).str.strip()

        # Drop rows with empty codes
        cci = cci[cci["column1_code"].str.len() > 0]
        cci = cci[cci["column2_code"].str.len() > 0]

        # Convert dates from YYYYMMDD integers to strings
        if "effective_date" in cci.columns:
            cci["effective_date"] = cci["effective_date"].astype(str).str.strip()
        if "deletion_date" in cci.columns:
            cci["deletion_date"] = cci["deletion_date"].astype(str).str.strip()
            cci["deletion_date"] = cci["deletion_date"].replace({"*": None, "nan": None, "": None})
        if "modifier_indicator" in cci.columns:
            cci["modifier_indicator"] = cci["modifier_indicator"].astype(str).str.strip()

        # Filter out deleted edits (deletion_date is set and not '*'/null)
        # Keep rows where deletion_date is null/empty (still active)
        cci = cci[cci["deletion_date"].isna() | (cci["deletion_date"] == "")]

        # Deduplicate
        cci = cci.drop_duplicates(subset=["column1_code", "column2_code"], keep="first")

        cci.to_sql("cci_edits", conn, if_exists="append", index=False)
        print(f"Loaded {len(cci)} CCI edit pairs")
    else:
        raise FileNotFoundError(
            f"CCI edits not found in {DATA_DIR}. "
            "Place the real CMS CCI file in backend/data/ before seeding."
        )

    # ── Load state laws ──
    laws_path = os.path.join(DATA_DIR, "state_laws.json")
    if os.path.exists(laws_path):
        with open(laws_path, "r") as f:
            state_laws = json.load(f)
        df_laws = pd.DataFrame(state_laws)
        df_laws.to_sql("state_laws", conn, if_exists="append", index=False)
        print(f"Loaded {len(df_laws)} state law entries")
    else:
        raise FileNotFoundError(
            f"State laws not found at {laws_path}. "
            "Place backend/data/state_laws.json before seeding."
        )

    # ── Create indexes ──
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cpt ON medicare_rates(cpt_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cci_col1 ON cci_edits(column1_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cci_col2 ON cci_edits(column2_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_laws ON state_laws(state_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_laws_category ON state_laws(state_code, category)")
    conn.commit()

    # ── Print summary ──
    cpt_count = conn.execute("SELECT COUNT(*) FROM medicare_rates").fetchone()[0]
    cci_count = conn.execute("SELECT COUNT(*) FROM cci_edits").fetchone()[0]
    law_count = conn.execute("SELECT COUNT(*) FROM state_laws").fetchone()[0]
    conn.close()

    print(f"\nDatabase seeded successfully!")
    print(f"  {cpt_count} CPT codes")
    print(f"  {cci_count} CCI edit pairs")
    print(f"  {law_count} state law entries")


def _load_clfs(conn):
    """Load Clinical Laboratory Fee Schedule from the CLFS CSV file."""
    # Find the CLFS file — name varies by quarter (e.g., "CLFS 2026 Q1V1.csv")
    clfs_files = _glob.glob(os.path.join(DATA_DIR, "CLFS*.csv")) + _glob.glob(os.path.join(DATA_DIR, "clfs*.csv"))
    if not clfs_files:
        print("  No CLFS file found in data/ — skipping lab rates")
        return

    clfs_path = clfs_files[0]
    # 4 header/copyright rows, row 5 has column names
    df = pd.read_csv(clfs_path, skiprows=4, low_memory=False, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]

    # Rename to our names
    rename = {}
    for col in df.columns:
        upper = col.upper()
        if upper == "HCPCS":
            rename[col] = "cpt_code"
        elif upper == "RATE":
            rename[col] = "rate"
        elif upper == "MOD":
            rename[col] = "mod"
        elif upper in ("SHORTDESC", "SHORT_DESC"):
            rename[col] = "short_desc"
        elif upper in ("LONGDESC", "LONG_DESC"):
            rename[col] = "long_desc"
    df = df.rename(columns=rename)

    if "cpt_code" not in df.columns or "rate" not in df.columns:
        print(f"  WARNING: CLFS columns not recognized. Found: {list(df.columns)[:10]}")
        return

    # Filter to base codes only (blank modifier)
    if "mod" in df.columns:
        df = df[df["mod"].isna() | (df["mod"].astype(str).str.strip() == "")]

    # Use short description, fall back to long description
    if "short_desc" in df.columns:
        df["description"] = df["short_desc"]
    elif "long_desc" in df.columns:
        df["description"] = df["long_desc"]
    else:
        df["description"] = None

    # Clean up
    df["cpt_code"] = df["cpt_code"].astype(str).str.strip()
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")

    # Drop rows with no rate or zero rate
    df = df[df["rate"].notna() & (df["rate"] > 0)]

    # Deduplicate by cpt_code
    df = df.drop_duplicates(subset=["cpt_code"], keep="first")

    # Insert into medicare_rates (labs use same price for facility/non-facility)
    lab_rows = [
        (row["cpt_code"], row["description"], row["rate"], row["rate"], "A")
        for _, row in df.iterrows()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO medicare_rates (cpt_code, description, non_facility_price, facility_price, status_code) VALUES (?, ?, ?, ?, ?)",
        lab_rows,
    )
    print(f"Loaded {len(lab_rows)} lab/clinical rates from CLFS ({os.path.basename(clfs_path)})")


if __name__ == "__main__":
    seed_database()
