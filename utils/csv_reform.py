import csv


with open("old_data.csv", "r", encoding="utf-8") as input_file:
    with open("new_data.csv", "w", encoding="utf-8") as output_file:
        reader = csv.DictReader(input_file)
        fieldnames = [
            "id",
            "role",
            "full_name",
            "phone",
            "address",
            "balance",
            "inviter_id",
        ]
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            row["address"] = (
                row["city"]
                + " "
                + row["street"]
                + " дом "
                + row["house"]
                + " строение "
                + row["building"]
                + " квартира "
                + row["apartament"]
            )
            new_row = {}
            for fieldname in fieldnames:
                new_row[fieldname] = row[fieldname]
            writer.writerow(new_row)
