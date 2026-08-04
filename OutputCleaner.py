from datetime import datetime
import re


def process_records(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    clean_records = []
    flagged_records = []
    seen_records = {}

    for raw_record in raw_records:
        reason = ""
        invoice_id = raw_record.get("invoice_id")

        # Check duplication before processing other fields
        duplicate_reason = check_duplicate(
            invoice_id,
            raw_record,
            seen_records
        )

        if duplicate_reason:
            # Keep the duplicate record unchanged because
            # vendor, date, and amount are not processed
            processed_record = raw_record.copy()
            processed_record["reason"] = duplicate_reason

            flagged_records.append(processed_record)

            # Skip the remaining checks and move to the next record
            continue

        # Get vendor and date
        vendor = raw_record.get("vendor")
        date = raw_record.get("date")
        amount = raw_record.get("amount")

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
            "date": date,
            "amount": amount
        }

        amount, amount_reason = check_amount(amount)
        if amount_reason:
            if reason:
                reason += ", "
            reason += amount_reason

        
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

            # Check whether the date is before 2023
            if parsed_date.year < 2023:
                return iso_date, "Date is before 2023"

            return iso_date, ""

        except ValueError:
            continue

    return date_value, "Invalid date format"


def check_amount(
    amount_value: str | int | float | None
) -> tuple[int | float | str, str]:
    """
    Checks and normalizes an invoice amount.

    Rules:
    - Missing, empty, spaces, or N/A are considered missing.
    - Removes a dollar sign from the beginning.
    - Removes commas.
    - Corrects common OCR character mistakes.
    - More than one OCR correction is flagged.
    - Unsupported characters cause processing to stop.
    - Values outside -1000 to 10000 are flagged.
    """

    # Check for a completely missing value
    if amount_value is None:
        return "", "Missing amount field"

    amount_text = str(amount_value).strip()

    # Check for an empty value, spaces, or N/A
    if not amount_text or amount_text.upper() == "N/A":
        return "", "Missing amount field"

    original_amount = amount_text

    # Remove a dollar sign only if it appears at the beginning
    if amount_text.startswith("$"):
        amount_text = amount_text[1:].strip()

    character_replacements = {
        "O": "0",
        "o": "0",
        "I": "1",
        "i": "1",
        "l": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "b": "8",
        "Z": "2",
        "z": "2"
    }

    allowed_characters = (
        set("0123456789,.-")
        | set(character_replacements.keys())
    )

    # Stop if an unsupported character exists
    for character in amount_text:
        if character not in allowed_characters:
            return (
                original_amount,
                f"Invalid character '{character}' in amount"
            )

    correction_count = 0
    corrected_characters = []

    # Replace common OCR mistakes
    for character in amount_text:
        if character in character_replacements:
            corrected_characters.append(
                character_replacements[character]
            )
            correction_count += 1
        else:
            corrected_characters.append(character)

    amount_text = "".join(corrected_characters)

    # Remove thousands-separator commas
    amount_text = amount_text.replace(",", "")

    # Accept values such as 1200, -450, 950.5, and .50
    valid_amount_pattern = r"-?(?:\d+(?:\.\d+)?|\.\d+)"

    if not re.fullmatch(valid_amount_pattern, amount_text):
        return original_amount, "Invalid amount format"

    number = float(amount_text)

    # Convert 1200.00 to 1200, but keep 950.5 as a float
    if number.is_integer():
        normalized_amount: int | float = int(number)
    else:
        normalized_amount = number

    reasons = []

    # Flag only when more than one OCR character was corrected
    if correction_count > 1:
        reasons.append(
            f"Multiple OCR character corrections: {correction_count}"
        )

    # Flag values outside the accepted range
    if normalized_amount < -1000 or normalized_amount > 10000:
        reasons.append("Unusual invoice amount")

    return normalized_amount, ", ".join(reasons)


def check_duplicate(
    invoice_id: str | None,
    current_record: dict,
    seen_records: dict
) -> str:
    """
    Checks whether the invoice ID has already appeared.

    The first occurrence is stored in seen_records.
    Later occurrences are marked as duplicates.
    """

    # Skip duplicate checking when the invoice ID is missing
    if not invoice_id:
        return ""

    # First occurrence of this invoice ID
    if invoice_id not in seen_records:
        seen_records[invoice_id] = current_record.copy()
        return ""

    first_record = seen_records[invoice_id]

    fields_to_compare = [
        "vendor",
        "date",
        "amount"
    ]

    same_values = all(
        current_record.get(field) == first_record.get(field)
        for field in fields_to_compare
    )

    if same_values:
        return f"Duplicated record with {invoice_id}"

    return f"Duplicated record {invoice_id} with distinct values"


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
        "date": "Oct 6, 2022",
        "vendor": ""
    }
]

clean_res, flagged_rec = process_records(raw_records)

# test_amounts = [
#     "$1,200.00",
#     "95O.5",
#     "9so.5",
#     "N/A",
#     "-450",
#     "9x0.5"
# ]

# for test_amount in test_amounts:
#     print(test_amount, "->", check_amount(test_amount))


# seen_records = {}

# test_records = [
#     # First appearance — not duplicated
#     {
#         "invoice_id": "INV-1001",
#         "vendor": "Acme Corp",
#         "date": "2024-01-05",
#         "amount": "$1,200.00"
#     },

#     # Same ID and same values — exact duplicate
#     {
#         "invoice_id": "INV-1001",
#         "vendor": "Acme Corp",
#         "date": "2024-01-05",
#         "amount": "$1,200.00"
#     },

#     # Same ID but different amount
#     {
#         "invoice_id": "INV-1001",
#         "vendor": "Acme Corp",
#         "date": "2024-01-05",
#         "amount": "$1,500.00"
#     },

#     # New ID — not duplicated
#     {
#         "invoice_id": "INV-1002",
#         "vendor": "Example Ltd",
#         "date": "2024-02-10",
#         "amount": "500"
#     },

#     # Same ID as INV-1002 but different vendor
#     {
#         "invoice_id": "INV-1002",
#         "vendor": "Different Vendor",
#         "date": "2024-02-10",
#         "amount": "500"
#     }
# ]


# for record in test_records:
#     duplicate_reason = check_duplicate(
#         record.get("invoice_id"),
#         record,
#         seen_records
#     )

#     print(record["invoice_id"], "->", duplicate_reason)