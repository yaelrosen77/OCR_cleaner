from datetime import datetime


def process_records(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    clean_records = []
    flagged_records = []

    for raw_record in raw_records:
        reason = ""

        # Get vendor and date
        vendor = raw_record.get("vendor")
        date = raw_record.get("date")

        # Check vendor
        vendor, vendor_reason = check_vendor(vendor)

        if vendor_reason:
            if reason:
                reason += ", "
            reason += vendor_reason

        # Check date
        date, date_reason = check_date(date)

        if date_reason:
            if reason:
                reason += ", "
            reason += date_reason

        processed_record = {
            "vendor": vendor,
            "date": date
        }

        if reason:
            processed_record["reason"] = reason
            flagged_records.append(processed_record)
        else:
            clean_records.append(processed_record)

    return clean_records, flagged_records


def check_vendor(vendor: str | None) -> tuple[str, str]:
    """
    Checks whether the vendor field is missing.
    No normalization is performed yet.
    """

    if not vendor:
        return "", "Missing vendor field"

    return vendor, ""


def check_date(date_value: str | None) -> tuple[str, str]:
    """
    Checks whether the date exists and matches an accepted format.

    Accepted formats:
    Jan 4, 2024
    01/06/2024
    2019-01-10

    Valid dates are converted to ISO format: YYYY-MM-DD.
    """

    if not date_value:
        return "", "Missing date field"

    date_value = date_value.strip()

    if not date_value:
        return "", "Missing date field"

    accepted_formats = [
        "%b %d, %Y",  # Jan 4, 2024
        "%m/%d/%Y",   # 01/06/2024
        "%Y-%m-%d"    # 2019-01-10
    ]

    for date_format in accepted_formats:
        try:
            parsed_date = datetime.strptime(date_value, date_format)
            iso_date = parsed_date.strftime("%Y-%m-%d")

            return iso_date, ""

        except ValueError:
            continue

    return date_value, "Invalid date format"


raw_records = [
    {
        "invoice_id": "INV-1001",
        "amount": "$1,200.00",
        "date": "2024-01-40",
        "vendor": "Acme Corp"
    },
    {
        "invoice_id": "INV-1004",
        "amount": "2,340",
        "date": "Jan 8, 2024",
        "vendor": ""
    },
    {
        "invoice_id": "INV-1005",
        "amount": "400",
        "date": "01/06/2024",
        "vendor": "Example Ltd"
    },
    {
        "invoice_id": "INV-1006",
        "amount": "500",
        "date": "",
        "vendor": ""
    }
]

clean_res, flagged_rec = process_records(raw_records)

print("Clean records:")
print(clean_res)

print("Flagged records:")
print(flagged_rec)