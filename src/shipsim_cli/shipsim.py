# This file is part of shipsim-cli.
# Copyright (C) 2025 espehon
# Licensed under the GNU General Public License v3.0
# See <https://www.gnu.org/licenses/gpl-3.0.html> for details.


#region Imports
import sys
import os
import argparse
import json
import importlib.metadata


import pandas as pd
import questionary



#endregion Imports
#region Setup


# Set settings file
settings_file = os.path.expanduser("~/.config/shipsim/settings.json").replace("\\", "/")
if os.path.exists(settings_file):
    with open(settings_file, "r") as f:
        settings = json.load(f)
else:
    settings = {
        "carriers_folder": os.path.expanduser("~/.local/share/shipsim").replace("\\", "/")
    }
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=4)
        print(f"Created settings file found at {settings_file}")

# Set carriers folder
if os.path.exists(settings["carriers_folder"]) == False:
    os.makedirs(settings["carriers_folder"])
    print(f"Created carriers folder at {settings['carriers_folder']}")
    

if len(os.listdir(settings["carriers_folder"])) == 0:
    print("\nNo carriers found in the carriers folder. Please add some carriers to the following:")
    print(settings["carriers_folder"])
    print("\nTry 'shipsim --help' for more info.")
    sys.exit(0)





# Set Argparse
parser = argparse.ArgumentParser(
    description="shipsim-cli: TODO.",
    epilog="TODO",
    allow_abbrev=False,
    add_help=False,
    usage="shipsim <FromZip> <ToZip> <PkgWeight1> [<PkgWeight2> ...]",
)

parser.add_argument('-?', '--help', action='help', help='Show this help message and exit.')
parser.add_argument('shipment_info', nargs=argparse.REMAINDER, help='<FromID> <ToZip> <PkgWeight>')




#endregion Setup
#region Functions


def folder_sys_help():
    print(f"Please set up your carriers in {settings['carriers_folder']}.")
    print("Each carrier should be a folder named after the carrier.")
    print("Inside each carrier folder, there should be a ZoneMap.csv and a RateCard.csv file.")
    print("Optionally, you can also add Misc.json for additional information like accessorials.")
    print("""\nExample:
    shipsim/
        ├── UPS/
        │   ├── ZoneMap.csv
        │   ├── RateCard.csv
        │   └── Misc.json
        └── FedEx/
            ├── ZoneMap.csv
            └── RateCard.csv\n""")


def get_carriers() -> list:
    """
    Get a list of carriers from the carriers folder.
    Returns:
        list: List of carrier names.
    """
    carriers = []
    for item in os.listdir(settings["carriers_folder"]):
        if os.path.isdir(os.path.join(settings["carriers_folder"], item)):
            carriers.append(item)
    return carriers


def pick_column(prompt, default_names, columns):
        """
        Check if an expected column is present in the DataFrame.
        If not, prompt the user to select from available columns.

        prompt: str - The prompt to display to the user.
        default_names: list - List of expected column names.
        columns: list - List of available column names in the DataFrame.

        Returns:
            str: The selected column name.
        """
        columns = [str(col) for col in columns]  # Ensure all column names are strings
        for name in default_names:
            if name in columns:
                return name
        # Prompt user if not found
        return questionary.select(
            f"Select the column for {prompt}:",
            choices=columns
        ).ask()


def shipsim(requests: list) -> pd.DataFrame:
    """
    Flexible shipping rate calculator.
    requests: list of dicts or DataFrame, must include 'from_id', 'to_zip', 'pkg_weight'.
    Other columns will be passed through to the output.
    """
    # Convert to DataFrame if needed
    if isinstance(requests, list):
        if len(requests) > 0 and isinstance(requests[0], dict):
            df_in = pd.DataFrame(requests)
        else:
            df_in = pd.DataFrame(requests, columns=["from_id", "to_zip", "pkg_weight"])
    else:
        df_in = requests.copy()

    columns = list(df_in.columns)

    from_col = pick_column("Origin ID (from_id)", ["from_id", "fromid", "origin", "origin_id"], columns)
    to_col = pick_column("Destination ZIP (to_zip)", ["to_zip", "tozip", "dest_zip", "destination", "destination_zip"], columns)
    weight_col = pick_column("Package Weight (pkg_weight)", ["pkg_weight", "weight", "pkgweight", "package_weight"], columns)

    # Ask user to select carriers
    carriers = get_carriers()
    if not carriers:
        folder_sys_help()
        sys.exit(0)
    selected_carriers = questionary.checkbox(
        "Select carriers to use:",
        choices=carriers
    ).ask()
    if not selected_carriers:
        print("Using all carriers.")
        selected_carriers = carriers
        
    # For each selected carrier, ask for shipping method if more than one
    carrier_methods = {}
    carrier_zonemaps = {}
    carrier_ratecards = {}
    carrier_accessorials = {}
    for carrier in selected_carriers:
        zones_map = pd.read_csv(
            os.path.join(settings["carriers_folder"], carrier, "ZoneMap.csv"),
            dtype=str
        )
        rate_card = pd.read_csv(
            os.path.join(settings["carriers_folder"], carrier, "RateCard.csv"),
            dtype=str
        )
        rate_card['Weight'] = rate_card['Weight'].astype(float)
        carrier_zonemaps[carrier] = zones_map
        carrier_ratecards[carrier] = rate_card

        # Check for Misc.json and accessorials
        misc_path = os.path.join(settings["carriers_folder"], carrier, "Misc.json")
        accessorial = None
        if os.path.exists(misc_path):
            with open(misc_path, "r") as f:
                misc = json.load(f)
                accessorial = misc.get("accessorials", None)
                if accessorial is not None:
                    try:
                        accessorial = float(accessorial)
                    except Exception:
                        accessorial = None
        carrier_accessorials[carrier] = accessorial

        shipping_methods = list(zones_map.columns[2:])
        if not shipping_methods:
            print(f"No shipping methods found in {carrier}'s ZoneMap.")
            continue
        if len(shipping_methods) > 1:
            method = questionary.select(
                f"Select shipping method for {carrier}:",
                choices=shipping_methods
            ).ask()
        else:
            method = shipping_methods[0]
        carrier_methods[carrier] = method
    output = []
    for idx, row_in in df_in.iterrows():
        from_id = row_in[from_col]
        to_zip = row_in[to_col]
        pkg = row_in[weight_col]
        for carrier in selected_carriers:
            zones_map = carrier_zonemaps[carrier]
            rate_card = carrier_ratecards[carrier]
            method = carrier_methods[carrier]
            accessorial = carrier_accessorials[carrier]

            # --- Zone/method/rate lookup ---
            match = zones_map.loc[
                (zones_map['Origin'] == str(from_id)) &
                (zones_map['ShipToZip3'] == str(to_zip)[:3])
            ]
            if match.empty or pd.isna(match.iloc[0][method]):
                print(f"Origin ID {from_id} with ShipToZip3 {str(to_zip)[:3]} not found for {method} in {carrier}'s ZoneMap.")
                continue
            to_zone = match.iloc[0][method]

            weights = rate_card['Weight'].values
            larger_weights = weights[weights >= float(pkg)]
            if larger_weights.size == 0:
                print(f"No rate found for {pkg} lbs (over max weight) from zone {to_zone} in {carrier} ({method}).")
                continue
            selected_weight = larger_weights.min()
            row = rate_card[rate_card['Weight'] == selected_weight]
            if row.empty or to_zone not in row.columns:
                print(f"No rate found for zone {to_zone} at weight {selected_weight} in {carrier} ({method}).")
                continue
            freight = float(row[to_zone].values[0])

            # --- Accessorial calculation ---
            if accessorial is not None:
                freight = round(freight * (1 + accessorial), 2)
                accessorial_flag = "Yes"
            else:
                accessorial_flag = "No"

            result_row = row_in.to_dict()  # Copy all user columns
            result_row.update({
                "Carrier": carrier,
                "Method": method,
                "Freight": freight,
                "Accessorial": accessorial_flag
            })
            output.append(result_row)

    output_df = pd.DataFrame(output)
    output_df = output_df.sort_values(by=[from_col, "Carrier", to_col, weight_col]).reset_index(drop=True)
    return output_df


def cli(argv=None):
    "shipsim 90001 10036 19.69"
    args = parser.parse_args(argv)
    packages = args.shipment_info[2:]
    payload =[]
    for package in packages:
        payload.append((args.shipment_info[0], args.shipment_info[1], float(package)))

    df = shipsim(payload)
    print(df.head(20))



#endregion Functions
#region Main

if __name__ == "__main__":
    print("This program file should not be run directly.\nPlease run __main__.py or the use the shipsim command instead.")
    sys.exit(0)



#endregion Main
