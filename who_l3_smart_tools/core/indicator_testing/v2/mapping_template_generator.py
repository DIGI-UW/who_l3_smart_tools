import yaml
import re
import pandas as pd  # added import for Excel processing


def generate_mapping_template(phenotype_excel, output_yaml):
    # Read the first two rows to extract meta information
    meta_df = pd.read_excel(phenotype_excel, header=None, nrows=2)
    # Assume row0 are headers and row1 are values
    headers = meta_df.iloc[0].tolist()
    values = meta_df.iloc[1].tolist()

    # Extract DAK ID from 'DAK ID' column if exists, else raise error
    if headers[0] == "DAK ID":
        dak_id = values[0]
    else:
        raise ValueError("DAK ID not found in phenotype_excel")

    meta_dict = dict(zip(headers, values))

    # After creating meta_dict, replace any NaN values with empty strings
    for k, v in meta_dict.items():
        if pd.isna(v):
            meta_dict[k] = ""

    # Prepare a clean, Markdown-formatted comment block highlighting key fields
    key_fields = [
        "Indicator definition",
        "Denominator calculation",
        "Numerator calculation",
        "Disaggregation data elements",
        "Numerator exclusions",
        "Denominator exclusions",
        "Category",
        "What it measures",
        "Rationale",
        "Method of measurement",
        "List of all data elements included in numerator and denominator",
    ]
    comment_lines = []
    for field in key_fields:
        val = meta_dict.get(field, "")

        # Convert to string if not already
        if not isinstance(val, str):
            val = str(val)

        # Heading line
        comment_lines.append(f"# **{field}**")
        if (
            field
            in (
                "Disaggregation data elements",
                "List of all data elements included in numerator and denominator",
            )
            and val
        ):
            # Blank line after heading
            comment_lines.append("#")
            for item in [
                itm.strip() for itm in re.split(r"[\n,]+", val) if itm.strip()
            ]:
                comment_lines.append(f"#   - {item}")
        else:
            # Split multiline text and comment out each line
            if val.strip():
                for line in val.splitlines():
                    comment_lines.append(f"#   {line}")
            else:
                comment_lines.append("#   ")
        # Add a blank line for spacing
        comment_lines.append("#")

    commented_meta = "\n".join(comment_lines) + "\n\n"

    # Read feature data using candidate header row (row 4, i.e. header=3)
    df = pd.read_excel(phenotype_excel, header=3)

    # Create mapping template with features as an indexed list
    mapping_template = {
        "dak_id": dak_id,
        "patient_profile": "HivPatient",
        "reporting_period": {
            "start": "2025-01-01",
            "end": "2025-01-30",
        },
        "features": [],
    }

    # Define feature columns to ignore
    ignore_features = {
        "Indicator Definition Overview",
        "List of related DAK Concepts",
        "Patient Phenotype ID",
        "Phenotype Description",
        "Counted as Numerator (0,1)",
        "Counted as Denominator (0,1)",
    }

    feature_counter = 0
    for col in df.columns:
        # Skip if header is not a non-empty string or starts with "Unnamed" or is in ignore_features
        if (
            not isinstance(col, str)
            or not col.strip()
            or col.startswith("Unnamed")
            or col in ignore_features
        ):
            continue
        unique_values = df[col].dropna().unique()
        feature_entry = {
            "name": col,
            "id": str(feature_counter),  # unique id for this feature column
            "target_profile": "",  # placeholder for target FHIR profiles
            "target_valueset": "",  # placeholder for target valuesets
            "target_fhir_path": "",  # placeholder for target FHIR path
            "values": [],  # sublist for each unique value mapping
        }
        for val in unique_values:
            feature_entry["values"].append(
                {"phenotype_value": str(val), "fhir_value": ""}
            )
        mapping_template["features"].append(feature_entry)
        feature_counter += 1

    # Write the clean commented meta and YAML mapping template to file
    with open(output_yaml, "w") as f:
        f.write(commented_meta)
        yaml.dump(mapping_template, f, default_flow_style=False)
    print(f"Mapping template YAML generated: {output_yaml}")
