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
        "carriers_folder": "~/.local/share/shipsim"
    }
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=4)
        print(f"Created settings file found at {settings_file}")

# Set carriers folder
if os.path.exists(settings["carriers_folder"]) == False:
    os.makedirs(settings["carriers_folder"])
    print(f"Created carriers folder at {settings['carriers_folder']}")

if os.listdir(settings["carriers_folder"]) == False:
    print("No carriers found in the carriers folder. Please add some carriers to the following:")
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
parser.add_argument('shipment_info', nargs=argparse.REMAINDER, help='<FromZip> <ToZip> <PkgWeight>')




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


def shipsim(from_zip: str, to_zip: str, pkg_weights: list) -> list:
    """
    Main function to calculate shipping rates.
    Args:
        from_zip (str): The ZIP code of the sender.
        to_zip (str): The ZIP code of the recipient.
        pkg_weights (list): List of package weights.
    """
    carriers = get_carriers()
    if not carriers:
        folder_sys_help()
        sys.exit(0)

    output = []

    for carrier in carriers:
        zones_map = pd.read_csv(os.path.join(settings["carriers_folder"], carrier, "ZoneMap.csv"))
        rate_card = pd.read_csv(os.path.join(settings["carriers_folder"], carrier, "RateCard.csv"))
        for pkg in pkg_weights:
            pass # todo
            
            




def cli(argv=None):
    "shipsim 90001 10036 19.69"
    args = parser.parse_args(argv)



#endregion Functions
#region Main

if __name__ == "__main__":
    print("This program file should not be run directly.\nPlease run __main__.py or the use the shipsim command instead.")
    sys.exit(0)



#endregion Main
