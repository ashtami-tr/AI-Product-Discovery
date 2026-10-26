# AI Product Discovery
# clean product metadata and prepare a searchable catalogue

from pathlib import Path
import gzip
import json
import pandas as pd

# project paths

PROJECT_DIR = Path(__file__).resolve().parent
LISTINGS_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "abo-listings"
    / "listings"
    / "metadata"
)

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

# extract readable text from multilingual metadata fields

def extract_text(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and item.get("value") is not None:
                parts.append(str(item["value"]))
        return " | ".join(parts)
    if isinstance(value, dict) and value.get("value") is not None:
        return str(value["value"])
    return ""

# read product records from the compressed metadata files

def load_products(limit_per_file=1000):
    records = []
    files = sorted(LISTINGS_DIR.glob("*.json.gz"))
    if not files:
        raise FileNotFoundError(
            f"No metadata files found in: {LISTINGS_DIR}"
        )
    print("reading product metadata...")
    for file_path in files:
        count = 0
        with gzip.open(
            file_path,
            "rt",
            encoding="utf-8"
        ) as file:
            for line in file:
                if not line.strip():
                    continue
                record = json.loads(line)
                # skip unexpected record formats
                if not isinstance(record, dict):
                    continue
                records.append(record)
                count += 1
                # limit the initial sample to keep it manageable
                if count >= limit_per_file:
                    break
        print(f"{file_path.name}: {count} records")
    return records

# convert the raw records into a consistent table

def create_catalogue(records):
    products = []
    for record in records:
        product = {
            "product_id": record.get("item_id", ""),
            "title": extract_text(record.get("item_name")),
            "brand": extract_text(record.get("brand")),
            "category": extract_text(record.get("product_type")),
            "colour": extract_text(record.get("color")),
            "keywords": extract_text(record.get("item_keywords")),
            "description": extract_text(record.get("bullet_point")),
            "main_image_id": record.get("main_image_id", ""),
            "other_image_ids": extract_text(
                record.get("other_image_id")
            ),
            "marketplace": record.get("domain_name", ""),
            "country": record.get("country", ""),
        }
        products.append(product)
    catalogue = pd.DataFrame(products)

    # remove records without a usable product identifier or title
    catalogue = catalogue.drop_duplicates(
        subset=["product_id", "marketplace"]
    )
    catalogue = catalogue[
        catalogue["product_id"].astype(str).str.strip().ne("")
        & catalogue["title"].astype(str).str.strip().ne("")
    ]
    return catalogue.reset_index(drop=True)

# save the catalogue and display a small preview

def save_catalogue(catalogue):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "product_catalogue.csv"
    catalogue.to_csv(output_path, index=False, encoding="utf-8-sig")
    print("\ncatalogue created successfully!")
    print("number of products:", len(catalogue))
    print("saved to:", output_path)
    print("\nfirst five products:")
    print(
        catalogue[
            [
                "product_id",
                "title",
                "category",
                "main_image_id",
            ]
        ].head().to_string(index=False)
    )
    print("\nmissing values:")
    print(
        catalogue[
            ["title", "category", "main_image_id"]
        ].replace("", pd.NA).isna().sum()
    )

# main function

def main():
    print("AI PRODUCT DISCOVERY")
    records = load_products(limit_per_file=1000)
    catalogue = create_catalogue(records)
    save_catalogue(catalogue)
    print("\nnext, we will connect product records to their images.")
if __name__ == "__main__":
    main()

# test the connection between products and images

catalogue_path = "data/processed/product_catalogue.csv"
image_metadata_path = "data/raw/images/metadata/images.csv.gz"

# load the product catalogue

products = pd.read_csv(catalogue_path)

# load the image mapping

images = pd.read_csv(image_metadata_path, compression="gzip")

# connect each product to its image path

products = products.merge(
    images[["image_id", "path"]],
    left_on="main_image_id",
    right_on="image_id",
    how="left"
)

# show the results

print("\nimage mapping test")
print(products[["product_id", "title", "main_image_id", "path"]].head(10))
print("\nproducts with a matched image:", products["path"].notna().sum())
print("products without a matched image:", products["path"].isna().sum())