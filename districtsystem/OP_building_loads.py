import os
from functools import reduce
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

# import nbimporter
# # Import the notebook from a specific folder
# import sys
# sys.path.append('District system - Engineering model')
# import UCSB_Loads_and_usage
# year = "UCSB_Loads and usage".year
from districtsystem.inputs import dateTime, weather_df

#############################################  define inputs ######################################################

#### change years if needed ###########
# current year of simulation - pick between 2045(decarb) or 2025(no decarb)
year = 2045
# base year for billing calc.
base_year = 2022

# Load the DataFrame from the pickle file from the CUP module

# if year > year of decarb then we will have key outputs from the New CUP module, else no key outputs
if year == 2045:
    # this gets modified below
    key_outputs = pd.read_pickle("outputs/key_outputs.pkl")  # noqa: S301
    # this version remains the same
    key_outputs_OG = pd.read_pickle("outputs/key_outputs.pkl")  # noqa: S301
elif year == 2025:
    key_outputs = pd.read_excel("New CUP_Key ouputs_No values (No decarb).xlsx")
    key_outputs_OG = pd.read_excel("New CUP_Key ouputs_No values (No decarb).xlsx")


#########################  import Building COP and process load Data + clean up #######################################
buildingLoadData_df = pd.read_excel("UCSB merged baselines_COP_process load.xlsx", sheet_name="Analytics - V1 5-14")

# Strip whitespace from all elements in the column
buildingLoadData_df["Simulation_id"] = buildingLoadData_df["Simulation_id"].str.strip()

# Drop rows where the "CAAN" column is NaN
buildingLoadData_df = buildingLoadData_df.dropna(subset=["CAAN"])

# Convert the "CAAN" column to numeric type, coercing non-convertible values to NaN
buildingLoadData_df["CAAN"] = pd.to_numeric(buildingLoadData_df["CAAN"], errors="coerce")


####################### Process Load COP_df defined ###############
COP_df = pd.DataFrame()
COP_df["Names"] = ["COOLCOP", "HEATCOP", "KITCHCOP", "DHWCOP", "LAUNCOP", "Other"]
COP_df["Electric"] = ["Default", (1, 4), 0.8, 1, 2.5, 1]
COP_df["Gas"] = ["-", (0, 0.99), 0.5, 0.95, 0.8, 1]
COP_df["CHW"] = [-1, "-", "-", "-", "-", 1]
COP_df["HW/Steam"] = ["-", -1, "-", -1, "-", 1]
COP_df.set_index("Names", inplace=True)


##########################  upload PNNL profiles fo all utilites #######################################

# PNNL electric profiles
pnnl_hotWater_e_profiles_df = pd.read_excel("Building_PNNL_elec_profiles.xlsx", sheet_name="Hot Water Load (kbtu)")
pnnl_cooking_e_profiles_df = pd.read_excel("Building_PNNL_elec_profiles.xlsx", sheet_name="Cooking Load (kbtu)")
pnnl_laundry_e_profiles_df = pd.read_excel("Building_PNNL_elec_profiles.xlsx", sheet_name="Laundry Load (kbtu)")
pnnl_other_e_profiles_df = pd.read_excel("Building_PNNL_elec_profiles.xlsx", sheet_name="Other Process Load (kbtu)")

# PNNL gas profiles
pnnl_hotWater_g_profiles_df = pd.read_excel("Building_PNNL_gas_profiles.xlsx", sheet_name="Hot Water Load (kbtu)")
pnnl_cooking_g_profiles_df = pd.read_excel("Building_PNNL_gas_profiles.xlsx", sheet_name="Cooking Load (kbtu)")
pnnl_laundry_g_profiles_df = pd.read_excel("Building_PNNL_gas_profiles.xlsx", sheet_name="Laundry Load (kbtu)")
pnnl_other_g_profiles_df = pd.read_excel("Building_PNNL_gas_profiles.xlsx", sheet_name="Other Process Load (kbtu)")

# PNNL district CHW profiles
pnnl_hotWater_c_profiles_df = pd.read_excel("Building_PNNL_c_profiles.xlsx", sheet_name="Hot Water Load (kbtu)")
pnnl_cooking_c_profiles_df = pd.read_excel("Building_PNNL_c_profiles.xlsx", sheet_name="Cooking Load (kbtu)")
pnnl_laundry_c_profiles_df = pd.read_excel("Building_PNNL_c_profiles.xlsx", sheet_name="Laundry Load (kbtu)")
pnnl_other_c_profiles_df = pd.read_excel("Building_PNNL_c_profiles.xlsx", sheet_name="Other Process Load (kbtu)")

# PNNL district HW/steam profiles
pnnl_hotWater_s_profiles_df = pd.read_excel("Building_PNNL_s_profiles.xlsx", sheet_name="Hot Water Load (kbtu)")
pnnl_cooking_s_profiles_df = pd.read_excel("Building_PNNL_s_profiles.xlsx", sheet_name="Cooking Load (kbtu)")
pnnl_laundry_s_profiles_df = pd.read_excel("Building_PNNL_s_profiles.xlsx", sheet_name="Laundry Load (kbtu)")
pnnl_other_s_profiles_df = pd.read_excel("Building_PNNL_s_profiles.xlsx", sheet_name="Other Process Load (kbtu)")


######################################### calculate loads #######################################################

# building_loads_folder =  r"C:\Users\nikita.khatwani\Documents\UCSB\District sytem - Engineering model\District system - Engineering model\Building loads data"

# Get the path to the directory containing the script (main_package)
package_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate up one directory to get the package directory
main_package_dir = os.path.dirname(package_dir)


# The relative path to the folder containing the individual building data csvs
building_loads_folder = os.path.join(main_package_dir, "notebooks/Building loads data")

#  List of all files in the folder
files = os.listdir(building_loads_folder)
allBldgLoads_output = pd.DataFrame()
allBldgElecUse_output = pd.DataFrame()
allBldgGasUse_output = pd.DataFrame()

# Convert the "CAAN" column to integer type
buildingLoadData_df["CAAN"] = buildingLoadData_df["CAAN"].astype("Int64")
# Extract the cleaned CAAN values as a list
caan_list = buildingLoadData_df["CAAN"].tolist()

# loop through all files
for caan_no in caan_list:
    bldg_id = buildingLoadData_df.loc[buildingLoadData_df["CAAN"] == caan_no, "Simulation_id"].iloc[0]
    file_name = f"in_{bldg_id}.csv"
    # print("id",id)
    file_path = os.path.join(building_loads_folder, file_name)

    try:
        # Read the CSV file into a DataFrame
        buildingLoads_perSqFt_df = pd.read_csv(file_path)

    except FileNotFoundError:
        print(f"Error: File not found for CAAN {caan_no} with simulation ID {bldg_id}")

    except Exception as e:
        print(f"Error occurred while processing file {file_path}: {e!s}")

    bldg_id = bldg_id.replace("in_", "")
    # id = file.replace(".csv", "").strip()
    # Remove the "in_" prefix using str.replace()

    # print("caan_no",caan_no)
    area = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "Area [sf]"].iloc[0]
    coolCOP = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "COOLCOP"].iloc[0]
    heatCOP = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "HEATCOP"].iloc[0]

    # annual process usage
    e_annual_processUsage = buildingLoadData_df.loc[
        buildingLoadData_df["Simulation_id"] == bldg_id, "E_process (kBtu/sf)"
    ].iloc[0]
    g_annual_processUsage = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "G_process"].iloc[
        0
    ]
    c_annual_processUsage = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "C_process"].iloc[
        0
    ]
    s_annual_processUsage = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "S_process"].iloc[
        0
    ]

    program = buildingLoadData_df.loc[buildingLoadData_df["Simulation_id"] == bldg_id, "Program"].iloc[0]

    ################ PNNL profiles pulled as per program #######################
    # electric profiles
    hotWater_e_programProfiles = pnnl_hotWater_e_profiles_df[program]
    cooking_e_programProfiles = pnnl_cooking_e_profiles_df[program]
    laundry_e_programProfiles = pnnl_laundry_e_profiles_df[program]
    other_e_programProfiles = pnnl_other_e_profiles_df[program]

    # gas profiles
    hotWater_g_programProfiles = pnnl_hotWater_g_profiles_df[program]
    cooking_g_programProfiles = pnnl_cooking_g_profiles_df[program]
    laundry_g_programProfiles = pnnl_laundry_g_profiles_df[program]
    other_g_programProfiles = pnnl_other_g_profiles_df[program]

    # c profiles
    hotWater_c_programProfiles = pnnl_hotWater_c_profiles_df[program]
    cooking_c_programProfiles = pnnl_cooking_c_profiles_df[program]
    laundry_c_programProfiles = pnnl_laundry_c_profiles_df[program]
    other_c_programProfiles = pnnl_other_c_profiles_df[program]

    # s profiles
    hotWater_s_programProfiles = pnnl_hotWater_s_profiles_df[program]
    cooking_s_programProfiles = pnnl_cooking_s_profiles_df[program]
    laundry_s_programProfiles = pnnl_laundry_s_profiles_df[program]
    other_s_programProfiles = pnnl_other_s_profiles_df[program]

    #################### load calculation ##########

    ###### empty df ################
    buildingModule_output = pd.DataFrame()
    simulationThermalLoads_output = pd.DataFrame()
    simulationElecUse_output = pd.DataFrame()
    simulationGasUse_output = pd.DataFrame()

    # define dateTime and CAAN no.
    simulationThermalLoads_output["Timestamp"] = dateTime
    simulationThermalLoads_output["Building ID CAAN"] = [caan_no] * 8760

    simulationElecUse_output["Timestamp"] = dateTime
    simulationElecUse_output["Building ID CAAN"] = [caan_no] * 8760

    simulationGasUse_output["Timestamp"] = dateTime
    simulationGasUse_output["Building ID CAAN"] = [caan_no] * 8760

    # cooling and heating loads
    simulationThermalLoads_output["Cooling Load (kbtu)"] = buildingLoads_perSqFt_df["cooling.load.kBtu_per_sqft"] * area
    simulationThermalLoads_output["Heating Load (kbtu)"] = buildingLoads_perSqFt_df["heating.load.kBtu_per_sqft"] * area

    # heating anc cooling usage
    simulationElecUse_output["Cooling (kWh)"] = (
        simulationThermalLoads_output["Cooling Load (kbtu)"] / coolCOP
    ) * 0.29307107017
    if heatCOP in range(1, 5):
        simulationElecUse_output["Heating (kWh)"] = (
            simulationThermalLoads_output["Heating Load (kbtu)"] / heatCOP
        ) * 0.29307107017
        simulationGasUse_output["Heating (Therms)"] = [0] * 8760
    elif 0 < heatCOP < 1:
        # print("caan",caan_no,heatCOP)
        simulationElecUse_output["Heating (kWh)"] = [0] * 8760
        simulationGasUse_output["Heating (Therms)"] = (
            simulationThermalLoads_output["Heating Load (kbtu)"] / heatCOP
        ) * 0.01
    else:  # incase of district heating
        # print("caan2",caan_no,heatCOP)
        simulationElecUse_output["Heating (kWh)"] = [0] * 8760
        simulationGasUse_output["Heating (Therms)"] = [0] * 8760

    # electric process usage
    simulationElecUse_output["Hot Water (kWh)"] = (
        e_annual_processUsage * area * hotWater_e_programProfiles
    ) * 0.29307107017
    simulationElecUse_output["Cooking (kWh)"] = (
        e_annual_processUsage * area * cooking_e_programProfiles
    ) * 0.29307107017  # 0
    simulationElecUse_output["Laundry (kWh)"] = (
        e_annual_processUsage * area * laundry_e_programProfiles
    ) * 0.29307107017
    simulationElecUse_output["Other Process (kWh)"] = (
        e_annual_processUsage * area * other_e_programProfiles
    ) * 0.29307107017  # 0

    # electric process loads
    buildingModule_output["e_Hot Water Load (kbtu)"] = (
        simulationElecUse_output["Hot Water (kWh)"] * COP_df.loc["DHWCOP", "Electric"]
    )
    buildingModule_output["e_Cooking Load (kbtu)"] = (
        simulationElecUse_output["Cooking (kWh)"] * COP_df.loc["KITCHCOP", "Electric"]
    )
    buildingModule_output["e_Laundry Load (kbtu)"] = (
        simulationElecUse_output["Laundry (kWh)"] * COP_df.loc["LAUNCOP", "Electric"]
    )
    # buildingModule_output["e_Other Process Load (kbtu)"] = simulationElecUse_output["Other Process Load (kWh)"]*COP_df.loc["Other","Electric"]

    # gas process usage
    simulationGasUse_output["Hot Water (Therms)"] = (g_annual_processUsage * area * hotWater_g_programProfiles) * 0.01
    simulationGasUse_output["Cooking (Therms)"] = (g_annual_processUsage * area * cooking_g_programProfiles) * 0.01
    simulationGasUse_output["Laundry (Therms)"] = (g_annual_processUsage * area * laundry_g_programProfiles) * 0.01
    simulationGasUse_output["Other Process (Therms)"] = (g_annual_processUsage * area * other_g_programProfiles) * 0.01

    # gas process loads
    buildingModule_output["g_Hot Water Load (kbtu)"] = (
        simulationGasUse_output["Hot Water (Therms)"] * COP_df.loc["DHWCOP", "Gas"]
    )
    buildingModule_output["g_Cooking Load (kbtu)"] = (
        simulationGasUse_output["Cooking (Therms)"] * COP_df.loc["KITCHCOP", "Gas"]
    )
    buildingModule_output["g_Laundry Load (kbtu)"] = (
        simulationGasUse_output["Laundry (Therms)"] * COP_df.loc["LAUNCOP", "Gas"]
    )
    # buildingModule_output["g_Other Process Load (kbtu)"] = simulationGasUse_output["Other Process Load (Therms)"]*COP_df.loc["Other","Gas"]

    # CHW process loads
    buildingModule_output["c_Other Process Load (kbtu)"] = (
        c_annual_processUsage * area * other_c_programProfiles * COP_df.loc["Other", "CHW"]
    )

    # HW/Steam process loads
    buildingModule_output["s_Hot Water Load (kbtu)"] = (
        s_annual_processUsage * area * hotWater_s_programProfiles * COP_df.loc["DHWCOP", "HW/Steam"]
    )
    # buildingModule_output["s_Other Process Load (kbtu)"] = s_annual_processUsage*area*other_s_programProfiles*COP_df.loc["Other","HW/Steam"]

    # Total process loads
    simulationThermalLoads_output["Hot Water Load (kbtu)"] = (
        buildingModule_output["e_Hot Water Load (kbtu)"]
        + buildingModule_output["g_Hot Water Load (kbtu)"]
        + buildingModule_output["s_Hot Water Load (kbtu)"]
    )
    simulationThermalLoads_output["Cooking Load (kbtu)"] = (
        buildingModule_output["e_Cooking Load (kbtu)"] + buildingModule_output["g_Cooking Load (kbtu)"]
    )
    simulationThermalLoads_output["Laundry Load (kbtu)"] = (
        buildingModule_output["e_Laundry Load (kbtu)"] + buildingModule_output["g_Laundry Load (kbtu)"]
    )
    # simulationThermalLoads_output["Other Process Load (kbtu)"] = buildingModule_output["e_Other Process Load (kbtu)"]+buildingModule_output["g_Other Process Load (kbtu)"]+buildingModule_output["c_Other Process Load (kbtu)"]+buildingModule_output["s_Other Process Load (kbtu)"]

    ############### Loading other elec process load/usage(load=usage for these) directly from CS results ############
    simulationElecUse_output["Plug Loads (kWh)"] = (
        buildingLoads_perSqFt_df["equipment.elec.kBtu_per_sqft"] * area
    ) * 0.29307107017
    simulationElecUse_output["Lighting (kWh)"] = (
        buildingLoads_perSqFt_df["lighting.elec.kBtu_per_sqft"] * area
    ) * 0.29307107017
    simulationElecUse_output["Fans (kWh)"] = (
        buildingLoads_perSqFt_df["fans.elec.kBtu_per_sqft"] * area
    ) * 0.29307107017
    simulationElecUse_output["Pumps (kWh)"] = (
        buildingLoads_perSqFt_df["pumps.elec.kBtu_per_sqft"] * area
    ) * 0.29307107017
    # simulationElecUse_output["Misc. (kWh)"]= buildingLoads_perSqFt_df["misc.elec.kBtu_per_sqft"]*area

    allBldgLoads_output = pd.concat(
        [allBldgLoads_output, simulationThermalLoads_output], ignore_index=True
    )  # Concatenate new row to existing DataFra\\\\\]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]'
    allBldgElecUse_output = pd.concat(
        [allBldgElecUse_output, simulationElecUse_output], ignore_index=True
    )  # Concatenate new row to existing DataFra\\\\\]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]'
    allBldgGasUse_output = pd.concat(
        [allBldgGasUse_output, simulationGasUse_output], ignore_index=True
    )  # Concatenate new row to existing DataFra\\\\\]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]'


############# Current District Therm Op loads #############
building_meta_df = pd.read_excel("Building_MetaData_.xlsx", header=1)
current_district_therm_loads = pd.DataFrame()


# Define a function to check conditions for each building
def meets_district_cooling_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Decarb"]
        and row["Current District Cooling Y/N?"] == "Y"
    )
    return condition


# Define a function to check conditions for each building
def meets_district_heating_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Decarb"]
        and row["Current District Heating Y/N?"] == "Y"
    )
    return condition

    # Define a function to check conditions for each building


def meets_district_DHW_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Decarb"]
        and row["Current District Hot Water Y/N?"] == "Y"
    )
    return condition


def filtered_bldg_sum(
    building_meta_df,
    allBldg_output,
    meets_conditions1,
    meets_conditions2,
    meets_conditions3,
    meets_conditions4,
    df,
    building_type,
    usage,
    units,
):
    # cooling filter
    # Apply the condition check to filter buildings
    filtered_buildings_cooling = building_meta_df.apply(meets_conditions1, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_cooling = building_meta_df.loc[filtered_buildings_cooling, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_cooling = allBldg_output[
        allBldg_output["Building ID CAAN"].isin(filtered_building_ids_cooling)
    ]
    # print("type",type)
    # print("usage",usage)
    # print("filtered_building_ids_cooling ",filtered_building_ids_cooling)
    # print("filtered_building_ids_cooling ",filtered_buildings_cooling)
    # print("filtered_loads_usage_cooling ",filtered_loads_usage_cooling)
    # heating filter
    filtered_buildings_heating = building_meta_df.apply(meets_conditions2, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_heating = building_meta_df.loc[filtered_buildings_heating, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_heating = allBldg_output[
        allBldg_output["Building ID CAAN"].isin(filtered_building_ids_heating)
    ]

    # DHW filter
    filtered_buildings_DHW = building_meta_df.apply(meets_conditions3, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_DHW = building_meta_df.loc[filtered_buildings_DHW, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_DHW = allBldg_output[allBldg_output["Building ID CAAN"].isin(filtered_building_ids_DHW)]

    # Other filter
    filtered_buildings_other = building_meta_df.apply(meets_conditions4, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_other = building_meta_df.loc[filtered_buildings_other, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_other = allBldg_output[allBldg_output["Building ID CAAN"].isin(filtered_building_ids_other)]

    # Sum the cooling loads across all hours for these buildings
    if usage == "Load (kBtu)":
        df[f"Current {building_type} Cooling {usage}"] = filtered_loads_usage_cooling.groupby(
            allBldg_output["Timestamp"]
        )["Cooling Load (kbtu)"].sum()
        df[f"Current {building_type} Heating {usage}"] = filtered_loads_usage_heating.groupby(
            allBldg_output["Timestamp"]
        )["Heating Load (kbtu)"].sum()
        df[f"Current {building_type} Hot Water {usage}"] = filtered_loads_usage_DHW.groupby(
            allBldg_output["Timestamp"]
        )["Hot Water Load (kbtu)"].sum()
        if building_type != "District":
            df[f"Current {building_type} Cooking {usage}"] = filtered_loads_usage_other.groupby(
                allBldg_output["Timestamp"]
            )["Cooking Load (kbtu)"].sum()
            df[f"Current {building_type} Laundry {usage}"] = filtered_loads_usage_other.groupby(
                allBldg_output["Timestamp"]
            )["Laundry Load (kbtu)"].sum()
    else:
        df[f"Current {building_type} Heating {usage}"] = filtered_loads_usage_heating.groupby(
            allBldg_output["Timestamp"]
        )[f"Heating {units}"].sum()
        df[f"Current {building_type} Hot Water {usage}"] = filtered_loads_usage_DHW.groupby(
            allBldg_output["Timestamp"]
        )[f"Hot Water {units}"].sum()
        df[f"Current {building_type} Cooking {usage}"] = filtered_loads_usage_other.groupby(
            allBldg_output["Timestamp"]
        )[f"Cooking {units}"].sum()
        df[f"Current {building_type} Laundry {usage}"] = filtered_loads_usage_other.groupby(
            allBldg_output["Timestamp"]
        )[f"Laundry {units}"].sum()
        df[f"Current {building_type} Other Process {usage}"] = filtered_loads_usage_other.groupby(
            allBldg_output["Timestamp"]
        )[f"Other Process {units}"].sum()
        if usage == "Electricity Use (kWh)":
            df[f"Current {building_type} Cooling {usage}"] = filtered_loads_usage_cooling.groupby(
                allBldg_output["Timestamp"]
            )["Cooling (kWh)"].sum()

    # Reset the index to move timestamp back as a column and reset to default integer index
    df.reset_index(inplace=True)
    df["Ambient Air Wet Bulb Temp (F)"] = weather_df["Wet Bulb Temp (°F)"]
    return df


def filtered_bldg_differentBldgs(
    building_meta_df,
    allBldg_output,
    meets_conditions1,
    meets_conditions2,
    meets_conditions3,
    meets_conditions4,
    df,
    building_type,
    usage,
    units,
):
    # df["Timestamp"] = dateTime
    # cooling filter
    # Apply the condition check to filter buildings
    filtered_buildings_cooling = building_meta_df.apply(meets_conditions1, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_cooling = building_meta_df.loc[filtered_buildings_cooling, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_cooling = allBldg_output[
        allBldg_output["Building ID CAAN"].isin(filtered_building_ids_cooling)
    ]

    # filtered_loads_usage_cooling.reset_index(drop=True, inplace=True)
    # print("type",type)
    # print("usage",usage)
    # print("filtered_building_ids_cooling ",filtered_building_ids_cooling)
    # print("filtered_building_ids_cooling ",filtered_buildings_cooling)
    # print("filtered_loads_usage_cooling ",filtered_loads_usage_cooling)
    # heating filter
    filtered_buildings_heating = building_meta_df.apply(meets_conditions2, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_heating = building_meta_df.loc[filtered_buildings_heating, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_heating = allBldg_output[
        allBldg_output["Building ID CAAN"].isin(filtered_building_ids_heating)
    ]

    # filtered_loads_usage_heating.reset_index(drop=True, inplace=True)

    # DHW filter
    filtered_buildings_DHW = building_meta_df.apply(meets_conditions3, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_DHW = building_meta_df.loc[filtered_buildings_DHW, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_DHW = allBldg_output[allBldg_output["Building ID CAAN"].isin(filtered_building_ids_DHW)]

    # filtered_loads_usage_DHW.reset_index(drop=True, inplace=True)

    # Other filter
    filtered_buildings_other = building_meta_df.apply(meets_conditions4, axis=1)

    # Extract the Building ID CAAN values of buildings that meet the conditions
    filtered_building_ids_other = building_meta_df.loc[filtered_buildings_other, "Building ID CAAN"].tolist()

    # Filter cooling loads for buildings that meet the conditions
    filtered_loads_usage_other = allBldg_output[allBldg_output["Building ID CAAN"].isin(filtered_building_ids_other)]

    # filtered_loads_usage_other.reset_index(drop=True, inplace=True)

    if usage == "Load (kBtu)":
        df["cooling CAAN"] = filtered_loads_usage_cooling["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Cooling {usage}"] = filtered_loads_usage_cooling["Cooling Load (kbtu)"]

        df["heating CAAN"] = filtered_loads_usage_heating["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Heating {usage}"] = filtered_loads_usage_heating["Heating Load (kbtu)"]

        df["hot water CAAN"] = filtered_loads_usage_DHW["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Hot Water {usage}"] = filtered_loads_usage_DHW["Hot Water Load (kbtu)"]
        df1 = pd.DataFrame(df["cooling CAAN"])
        df2 = pd.DataFrame(df["heating CAAN"])
        df3 = pd.DataFrame(df["hot water CAAN"])
        df1.columns = ["Building ID CAAN"]
        df2.columns = ["Building ID CAAN"]
        df3.columns = ["Building ID CAAN"]

        # Merge DataFrames on the common column 'Key_Column'
        combined_df = df1.combine_first(df2)
        # print("merged_df",combined_df)
        # df["Building ID CAAN"] = merged_df["cooling CAAN"]
        # merged_df = pd.merge(merged_df, df4, left_on='cooling CAAN', right_on='heating CAAN', how='outer')
        if building_type != "District":
            df["cooking CAAN"] = filtered_loads_usage_other["Building ID CAAN"].astype(int)
            df[f"Current {building_type} Cooking {usage}"] = filtered_loads_usage_other["Cooking Load (kbtu)"]
            df["laundry CAAN"] = filtered_loads_usage_other["Building ID CAAN"].astype(int)
            df[f"Current {building_type} Laundry {usage}"] = filtered_loads_usage_other["Laundry Load (kbtu)"]
            df4 = pd.DataFrame(df["cooking CAAN"])
            df5 = pd.DataFrame(df["laundry CAAN"])
            df4.columns = ["Building ID CAAN"]
            df5.columns = ["Building ID CAAN"]
            combined_df = combined_df.combine_first(df4).combine_first(df5)
        df["Building ID CAAN"] = combined_df["Building ID CAAN"].astype(int)

    else:
        df["heating CAAN"] = filtered_loads_usage_heating["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Heating {usage}"] = filtered_loads_usage_heating[f"Heating {units}"]

        df["hot water CAAN"] = filtered_loads_usage_DHW["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Hot Water {usage}"] = filtered_loads_usage_DHW[f"Hot Water {units}"]

        df["cooking CAAN"] = filtered_loads_usage_other["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Cooking {usage}"] = filtered_loads_usage_other[f"Cooking {units}"]
        df["laundry CAAN"] = filtered_loads_usage_other["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Laundry {usage}"] = filtered_loads_usage_other[f"Laundry {units}"]
        df["other CAAN"] = filtered_loads_usage_other["Building ID CAAN"].astype(int)
        df[f"Current {building_type} Other Process {usage}"] = filtered_loads_usage_other[f"Other Process {units}"]

        df2 = pd.DataFrame(df["heating CAAN"])
        df3 = pd.DataFrame(df["hot water CAAN"])
        df4 = pd.DataFrame(df["cooking CAAN"])
        df5 = pd.DataFrame(df["laundry CAAN"])
        df6 = pd.DataFrame(df["other CAAN"])

        df2.columns = ["Building ID CAAN"]
        df3.columns = ["Building ID CAAN"]
        df4.columns = ["Building ID CAAN"]
        df5.columns = ["Building ID CAAN"]
        df6.columns = ["Building ID CAAN"]
        combined_df = df2.combine_first(df3).combine_first(df4).combine_first(df5).combine_first(df6)
        if usage == "Electricity Use (kWh)":
            df["cooling CAAN"] = filtered_loads_usage_cooling["Building ID CAAN"].astype(int)
            df[f"Current {building_type} Cooling {usage}"] = filtered_loads_usage_cooling["Cooling (kWh)"]
            df1 = pd.DataFrame(df["cooling CAAN"])
            df1.columns = ["Building ID CAAN"]
            combined_df = combined_df.combine_first(df1)
        df["Building ID CAAN"] = combined_df["Building ID CAAN"].astype(int)

    # Reset the index to move timestamp back as a column and reset to default integer index
    df = df.reset_index(drop=True)
    # Calculate the number of times to repeat the series
    num_repeats = len(df) // 8760
    # Create a new column with the repeated series
    df["Ambient Air Wet Bulb Temp (F)"] = np.tile(weather_df["Wet Bulb Temp (°F)"].values, num_repeats)
    df["Timestamp"] = np.tile(dateTime.values, num_repeats)
    return df


current_district_therm_loads = filtered_bldg_sum(
    building_meta_df,
    allBldgLoads_output,
    meets_district_cooling_conditions,
    meets_district_heating_conditions,
    meets_district_DHW_conditions,
    meets_district_DHW_conditions,
    current_district_therm_loads,
    "District",
    "Load (kBtu)",
    "(kBtu)",
)


################# bldg loads and usage #####################


# empty frame
current_bldg_therm_loads = pd.DataFrame()
current_bldg_elec_use = pd.DataFrame()
current_bldg_gas_use = pd.DataFrame()
new_bldg_therm_loads = pd.DataFrame()


########### building conditions #########################
# Define a function to check conditions for each building
def meets_building_cooling_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Decarb"]
        and row["Current District Cooling Y/N?"] == "N"
    )
    return condition


# Define a function to check conditions for each building
def meets_building_heating_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Decarb"]
        and row["Current District Heating Y/N?"] == "N"
    )
    return condition

    # Define a function to check conditions for each building


def meets_building_DHW_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Decarb"]
        and row["Current District Hot Water Y/N?"] == "N"
    )
    return condition


def meets_building_other_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year < row["Year of Cooking and Laundry Decarb"]
    )
    return condition


current_Bldg_Therm_Op_Loads = filtered_bldg_differentBldgs(
    building_meta_df,
    allBldgLoads_output,
    meets_building_cooling_conditions,
    meets_building_heating_conditions,
    meets_building_DHW_conditions,
    meets_building_other_conditions,
    current_bldg_therm_loads,
    "Building Equipment",
    "Load (kBtu)",
    "(kBtu)",
)
Current_Bldg_Equip_Elec_Use = filtered_bldg_differentBldgs(
    building_meta_df,
    allBldgElecUse_output,
    meets_building_cooling_conditions,
    meets_building_heating_conditions,
    meets_building_DHW_conditions,
    meets_building_other_conditions,
    current_bldg_elec_use,
    "Building Equipment",
    "Electricity Use (kWh)",
    "(kWh)",
)
Current_Bldg_Equip_Gas_Use = filtered_bldg_differentBldgs(
    building_meta_df,
    allBldgGasUse_output,
    meets_building_cooling_conditions,
    meets_building_heating_conditions,
    meets_building_DHW_conditions,
    meets_building_other_conditions,
    current_bldg_gas_use,
    "Building Equipment",
    "Gas Use (therms)",
    "(Therms)",
)


############
# Define a function to check conditions for each building
def meets_new_building_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year >= row["Year of Decarb"]
        and row["Decarbonization Type (New Building Heat Pumps vs. New CUP)"] == "New Building Heat Pumps"
    )
    return condition


def meets_new_building_other_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year >= row["Year of Cooking and Laundry Decarb"]
    )
    return condition


new_Bldg_Therm_Op_Loads = filtered_bldg_differentBldgs(
    building_meta_df,
    allBldgLoads_output,
    meets_new_building_conditions,
    meets_new_building_conditions,
    meets_new_building_conditions,
    meets_new_building_other_conditions,
    new_bldg_therm_loads,
    "New Building Independent Heat Pump",
    "Load (kBtu)",
    "(kBtu)",
)


######################## wet bulb / COP regression #######################

calculation_map_COP_wetbulb = pd.read_excel(
    "UCSB Calculation Map.xlsx", sheet_name="Reg. Data - Current District", header=1
)


def COP_wetbulb_reg(COP_wetbulb_reg_output, subset_training_data):
    # Define conditions for COP calculation based on wet bulb temperature
    COP_wetbulb_reg_output["Current District Cooling COP"] = np.where(
        (COP_wetbulb_reg_output["Current District Wet Bulb (F)"] <= 68),
        6,
        np.where(
            COP_wetbulb_reg_output["Current District Wet Bulb (F)"] >= 78,
            3,
            np.nan,  # Placeholder for values between 68 and 78 (handled in regression)
        ),
    )

    # Filter the range of wet bulb temperatures for regression (between 68 and 78)
    mask = (COP_wetbulb_reg_output["Current District Wet Bulb (F)"] > 68) & (
        COP_wetbulb_reg_output["Current District Wet Bulb (F)"] < 78
    )

    wet_bulb_temps_subset = COP_wetbulb_reg_output.loc[mask, "Current District Wet Bulb (F)"]

    if not wet_bulb_temps_subset.empty:
        # Prepare data for regression (subset from calculation map)
        X = sm.add_constant(subset_training_data["Current District Wet Bulb (F)"])
        y = subset_training_data["Current District Cooling COP"]

        # Fit OLS regression model
        model = sm.OLS(y, X).fit()

        # Generate a range of Wet Bulb Temperature values for prediction
        new_wet_bulb_temps = np.arange(wet_bulb_temps_subset.min(), wet_bulb_temps_subset.max() + 1)

        # Add constant term to the new values for prediction
        X_new = sm.add_constant(new_wet_bulb_temps)
        # print("jjjjjjjjj",new_wet_bulb_temps,X_new)
        # Predict Cooling COP for the new values using the fitted model
        predicted_cooling_cop_new = model.predict(X_new)

        # Update output DataFrame with predicted COP values
        COP_wetbulb_reg_output.loc[mask, "Current District Cooling COP"] = predicted_cooling_cop_new

        # Display model summary
        # print(model.summary())

    return COP_wetbulb_reg_output


# Subset the training data based on wet bulb temperature range
subset_training_data = calculation_map_COP_wetbulb[
    (calculation_map_COP_wetbulb["Current District Wet Bulb (F)"] > 67)
    & (calculation_map_COP_wetbulb["Current District Wet Bulb (F)"] < 79)
]


COP_wetbulb_reg_output = pd.DataFrame()
COP_wetbulb_reg_output["Current District Wet Bulb (F)"] = range(24, 91)

# Apply the COP regression function to calculate Cooling COP
COP_wetbulb_reg_output = COP_wetbulb_reg(COP_wetbulb_reg_output, subset_training_data)


##################### Current District Elec use ###############################


# empty frame
current_District_Elec_Use = pd.DataFrame()
# Round and convert to integer for temperature comparison
rounded_weather_temps = weather_df["Wet Bulb Temp (°F)"].round().astype(int)
wet_bulb_temps = COP_wetbulb_reg_output["Current District Wet Bulb (F)"]

# Find the index of the closest wet bulb temperature for each weather temperature
closest_indices = np.abs(wet_bulb_temps.values[:, None] - rounded_weather_temps.values).argmin(axis=0)

# Use the closest indices to retrieve corresponding COP values
assigned_cop_values = (
    COP_wetbulb_reg_output["Current District Cooling COP"].iloc[closest_indices].reset_index(drop=True)
)

# Assign the assigned COP values to the original DataFrame
current_District_Elec_Use["Current District Cooling COP_WB"] = assigned_cop_values

current_District_Elec_Use["Current District System Cooling Electricity Use (kWh)"] = (
    current_district_therm_loads["Current District Cooling Load (kBtu)"]
    / current_District_Elec_Use["Current District Cooling COP_WB"]
)


############################ Current District Gas use ###############################

current_District_Gas_Use = pd.DataFrame()

district_HW_COP = calculation_map_COP_wetbulb["Current District Heating COP"][0]
district_DHW_COP = calculation_map_COP_wetbulb["Current District Hot Water COP"][0]

current_District_Gas_Use["Current District System Heating Gas Use (therms)"] = (
    current_district_therm_loads["Current District Heating Load (kBtu)"] / district_HW_COP
)
current_District_Gas_Use["Current District System Hot Water Gas Use (therms)"] = (
    current_district_therm_loads["Current District Hot Water Load (kBtu)"] / district_DHW_COP
)


######################## new bldg regression #######################

calculation_map_hpCOP_drybulb = pd.read_excel(
    "UCSB Calculation Map.xlsx", sheet_name="Reg. Data - New Bldg Equip", header=1
)


def COP_dryBulb_newEquip_reg(subset_training_data, column):
    COP_newBldgEquip_reg_output = pd.DataFrame()
    # Prepare data for regression (subset from calculation map)
    X = sm.add_constant(subset_training_data["Ambient Air Dry Bulb Temp (F)"])
    y = subset_training_data[column]

    # Fit OLS regression model
    model = sm.OLS(y, X).fit()

    # Generate a range of Wet Bulb Temperature values for prediction
    new_dry_bulb_temps = np.arange(
        subset_training_data["Ambient Air Dry Bulb Temp (F)"].min(),
        subset_training_data["Ambient Air Dry Bulb Temp (F)"].max() + 1,
    )

    COP_newBldgEquip_reg_output["Ambient Air Dry Bulb Temp (F)"] = pd.Series(new_dry_bulb_temps)
    # Add constant term to the new values for prediction
    X_new = sm.add_constant(new_dry_bulb_temps)

    # print("jjjjjjjjj",new_wet_bulb_temps,X_new)
    # Predict Cooling COP for the new values using the fitted model
    predicted_cooling_cop_new = model.predict(X_new)

    # Update output DataFrame with predicted COP values
    COP_newBldgEquip_reg_output[column] = predicted_cooling_cop_new

    # Display model summary
    # print(model.summary())

    return COP_newBldgEquip_reg_output


## subset 1 ##
# Subset the training data based on wet bulb temperature range
subset_training_data_hpCOP = calculation_map_hpCOP_drybulb[
    (calculation_map_hpCOP_drybulb["Ambient Air Dry Bulb Temp (F)"] > 49)
]

# Drop rows with NaN in the specified column only
subset_training_data_hpCOP_cleaned = subset_training_data_hpCOP.dropna(
    subset=["New Building Independent Heat Pump - Cooling COP (44°F CHWST)"]
)

## subset 2 ##
# Subset the training data based on wet bulb temperature range
subset_training_data_hpHCOP = calculation_map_hpCOP_drybulb[
    (calculation_map_hpCOP_drybulb["Ambient Air Dry Bulb Temp (F)"] <= 65)
]

# Drop rows with NaN in the specified column only
subset_training_data_hpHCOP_cleaned = subset_training_data_hpHCOP.dropna(
    subset=["New Building Independent Heat Pump - Heating COP (170°F HWST)"]
)


## subset 3 ##
# Subset the training data based on wet bulb temperature range
subset_training_data_hpDHWCOP = calculation_map_hpCOP_drybulb[
    (calculation_map_hpCOP_drybulb["Ambient Air Dry Bulb Temp (F)"] <= 80)
]

# Drop rows with NaN in the specified column only
subset_training_data_hpDHWCOP_cleaned = subset_training_data_hpDHWCOP.dropna(
    subset=["New Building Independent Heat Pump - Hot Water COP"]
)


# Apply the COP regression function to calculate Cooling COP
COP_newBldgEquip_reg_output_1 = COP_dryBulb_newEquip_reg(
    subset_training_data_hpCOP_cleaned,
    "New Building Independent Heat Pump - Cooling COP (44°F CHWST)",
)
COP_newBldgEquip_reg_output_2 = COP_dryBulb_newEquip_reg(
    subset_training_data_hpHCOP_cleaned,
    "New Building Independent Heat Pump - Heating COP (170°F HWST)",
)
COP_newBldgEquip_reg_output_3 = COP_dryBulb_newEquip_reg(
    subset_training_data_hpDHWCOP_cleaned,
    "New Building Independent Heat Pump - Hot Water COP",
)
COP_newBldgEquip_reg_output_4 = COP_dryBulb_newEquip_reg(calculation_map_hpCOP_drybulb, "New Building Cooking COP")
COP_newBldgEquip_reg_output_5 = COP_dryBulb_newEquip_reg(calculation_map_hpCOP_drybulb, "New Building Laundry COP")

# List of DataFrame objects to be merged
dfs_to_merge = [
    COP_newBldgEquip_reg_output_1,
    COP_newBldgEquip_reg_output_2,
    COP_newBldgEquip_reg_output_3,
    COP_newBldgEquip_reg_output_4,
    COP_newBldgEquip_reg_output_5,
]

# Define the common key column for merging
key_column = "Ambient Air Dry Bulb Temp (F)"

# Use functools.reduce() with pd.merge() to merge all DataFrames in the list
COP_newBldgEquip_reg_output = reduce(
    lambda left, right: pd.merge(left, right, on=key_column, how="outer"), dfs_to_merge
)


##################### New Bldg equipment Elec use ###############################

########## change to many bldgs ############## I think I did ########


def cop_column(
    rounded_dryBulb_temps,
    dry_bulb_temps,
    COP_newBldgEquip_reg_output,
    column,
    loads_len,
):
    # Find the index of the closest wet bulb temperature for each weather temperature
    closest_indices_2 = np.abs(dry_bulb_temps.values[:, None] - rounded_dryBulb_temps.values).argmin(axis=0)

    # Use the closest indices to retrieve corresponding COP values
    assigned_cooling_cop_values = COP_newBldgEquip_reg_output[column].iloc[closest_indices_2].reset_index(drop=True)

    # Determine the length of each segment (8760)
    segment_length = len(assigned_cooling_cop_values)

    # Calculate the number of complete cycles
    num_cycles = loads_len // segment_length

    # Repeat COP values to match the length of load values
    cop_repeated = np.tile(assigned_cooling_cop_values, num_cycles)
    timeStamp_repeated = np.tile(dateTime, num_cycles)
    return cop_repeated, timeStamp_repeated


# empty frame
new_bldg_equip_elec_Use = pd.DataFrame()
# Round and convert to integer for temperature comparison
rounded_dryBulb_temps = weather_df["Dry Bulb Temp (°F)"].round().astype(int)
dry_bulb_temps = COP_newBldgEquip_reg_output["Ambient Air Dry Bulb Temp (F)"]

cop_timeline_col = cop_column(
    rounded_dryBulb_temps,
    dry_bulb_temps,
    COP_newBldgEquip_reg_output,
    "New Building Independent Heat Pump - Cooling COP (44°F CHWST)",
    new_Bldg_Therm_Op_Loads.shape[0],
)

# assigning timeStamp
new_bldg_equip_elec_Use["Timestamp"] = cop_timeline_col[1]
# assiging cooling COP
new_bldg_equip_elec_Use["Current New Bldg Cooling COP_DB"] = cop_timeline_col[0]
# cooling load to usage
new_bldg_equip_elec_Use["New Building Independent Heat Pump Cooling Electricity Use"] = (
    new_Bldg_Therm_Op_Loads["Current New Building Independent Heat Pump Cooling Load (kBtu)"]
    / new_bldg_equip_elec_Use["Current New Bldg Cooling COP_DB"]
)

# # Use the closest indices to retrieve corresponding COP values
# assigned_heating_cop_values = COP_newBldgEquip_reg_output["New Building Independent Heat Pump - Heating COP (170°F HWST)"].iloc[closest_indices].reset_index(drop=True)

# # Assign the assigned COP values to the original DataFrame
# new_bldg_equip_elec_Use["Current New Bldg Heating COP_WB"] = assigned_heating_cop_values

# assiging heating COP
new_bldg_equip_elec_Use["Current New Bldg Heating COP_DB"] = cop_column(
    rounded_dryBulb_temps,
    dry_bulb_temps,
    COP_newBldgEquip_reg_output,
    "New Building Independent Heat Pump - Heating COP (170°F HWST)",
    new_Bldg_Therm_Op_Loads.shape[0],
)[0]
# heating load to usage
new_bldg_equip_elec_Use["New Building Independent Heat Pump Heating Electricity Use (kWh)"] = (
    new_Bldg_Therm_Op_Loads["Current New Building Independent Heat Pump Heating Load (kBtu)"]
    / new_bldg_equip_elec_Use["Current New Bldg Heating COP_DB"]
)

# assiging hot water COP
new_bldg_equip_elec_Use["Current New Bldg Hot water COP_DB"] = cop_column(
    rounded_dryBulb_temps,
    dry_bulb_temps,
    COP_newBldgEquip_reg_output,
    "New Building Independent Heat Pump - Hot Water COP",
    new_Bldg_Therm_Op_Loads.shape[0],
)[0]
# hot water  to usage
new_bldg_equip_elec_Use["New Building Independent Heat Pump Hot Water Electricity Use (kWh)"] = (
    new_Bldg_Therm_Op_Loads["Current New Building Independent Heat Pump Hot Water Load (kBtu)"]
    / new_bldg_equip_elec_Use["Current New Bldg Hot water COP_DB"]
)


# assiging cooking COP
new_bldg_equip_elec_Use["Current New Bldg Cooking COP_DB"] = cop_column(
    rounded_dryBulb_temps,
    dry_bulb_temps,
    COP_newBldgEquip_reg_output,
    "New Building Cooking COP",
    new_Bldg_Therm_Op_Loads.shape[0],
)[0]
# cooking to usage
new_bldg_equip_elec_Use["New Building Equipment Cooking Electricity Use (kWh)"] = (
    new_Bldg_Therm_Op_Loads["Current New Building Independent Heat Pump Cooking Load (kBtu)"]
    / new_bldg_equip_elec_Use["Current New Bldg Cooking COP_DB"]
)

# assiging laundry COP
new_bldg_equip_elec_Use["Current New Bldg Laundry COP_DB"] = cop_column(
    rounded_dryBulb_temps,
    dry_bulb_temps,
    COP_newBldgEquip_reg_output,
    "New Building Laundry COP",
    new_Bldg_Therm_Op_Loads.shape[0],
)[0]
# laundry to usage
new_bldg_equip_elec_Use["New Building Equipment Laundry Electricity Use (kWh)"] = (
    new_Bldg_Therm_Op_Loads["Current New Building Independent Heat Pump Laundry Load (kBtu)"]
    / new_bldg_equip_elec_Use["Current New Bldg Laundry COP_DB"]
)


new_bldg_equip_elec_Use["Building ID CAAN"] = new_Bldg_Therm_Op_Loads["Building ID CAAN"]
######### newCUP ####################

new_CUP_therm_loads = pd.DataFrame()


# Define a function to check conditions for each building
def meets_new_CUP_conditions(row):
    condition = (
        year >= row["First Year Active"]
        and year <= row["Last Year Active"]
        and year >= row["Year of Decarb"]
        and row["Decarbonization Type (New Building Heat Pumps vs. New CUP)"] == "New CUP"
    )
    return condition


new_CUP_Therm_Loads = filtered_bldg_differentBldgs(
    building_meta_df,
    allBldgLoads_output,
    meets_new_CUP_conditions,
    meets_new_CUP_conditions,
    meets_new_CUP_conditions,
    meets_new_CUP_conditions,
    new_CUP_therm_loads,
    "New CUP",
    "Load (kBtu)",
    "(kBtu)",
)
new_CUP_Therm_Loads.to_pickle("new_CUP_Therm_Loads.pkl")

########### new CUP regression ##########################

if year == 2025:
    newCUp_reg_df = pd.DataFrame()

else:
    calculation_map_newCUP_regData = pd.read_excel(
        "UCSB Calculation Map.xlsx", sheet_name="Reg. Data - New CUP Equip", header=1
    )

    newCUp_reg_df = pd.DataFrame()

    def newCUp_reg(input_train, target_train, input_pred):
        from sklearn.linear_model import LinearRegression

        model = LinearRegression()
        model.fit(input_train, target_train)
        COP = model.predict(input_pred)
        return COP

    ## chiller COP ##

    # Rename columns in key_outputs to match those in calculation_map_newCUP_regData
    key_outputs = key_outputs.rename(
        columns={
            "Chiller-GrS-CHW Entering (F)": "Chiller Condenser EWT-1",
            "Chiller-OcS-CHW Entering (F)": "Chiller Condenser EWT-2",
            "Chiller-TS-CHW Entering (F)": "Chiller Condenser EWT-3",
            "Chiller-GrS-CHW Leaving (F)": "Chiller Evaporator LWT-1",
            "Chiller-OcS-CHW Leaving (F)": "Chiller Evaporator LWT-2",
            "Chiller-TS-CHW Leaving (F)": "Chiller Evaporator LWT-3",
        }
    )

    input_train_chiller = calculation_map_newCUP_regData[
        [
            "Chiller Condenser EWT-1",
            "Chiller Condenser EWT-1",
            "Chiller Condenser EWT-1",
            "Chiller Evaporator LWT-1",
            "Chiller Evaporator LWT-2",
            "Chiller Evaporator LWT-3",
        ]
    ]
    target_train_chiller = calculation_map_newCUP_regData["Chiller COP"]
    input_pred_chiller = key_outputs[
        [
            "Chiller Condenser EWT-1",
            "Chiller Condenser EWT-1",
            "Chiller Condenser EWT-1",
            "Chiller Evaporator LWT-1",
            "Chiller Evaporator LWT-2",
            "Chiller Evaporator LWT-3",
        ]
    ]

    newCUp_reg_df["Chiller COP"] = newCUp_reg(input_train_chiller, target_train_chiller, input_pred_chiller)

    ## HP COP - simultaneous ##

    # Rename columns in key_outputs to match those in calculation_map_newCUP_regData
    key_outputs = key_outputs.rename(
        columns={
            "HP_HC-CHW Entering (F)": "Heat Pump Simultaneous - Cold EWT",
            "HP_HC-CHW Leaving (F)": "Heat Pump Simultaneous - Cold LWT",
            "HP_HC-HHW Entering (F)": "Heat Pump Simultaneous - Hot EWT",
            "HP_HC-HHW Leaving (F)": "Heat Pump Simultaneous - Hot LWT",
        }
    )

    input_train_HP_sim = calculation_map_newCUP_regData[
        [
            "Heat Pump Simultaneous - Cold EWT",
            "Heat Pump Simultaneous - Cold LWT",
            "Heat Pump Simultaneous - Hot EWT",
            "Heat Pump Simultaneous - Hot LWT",
        ]
    ]
    target_train_HP_sim = calculation_map_newCUP_regData["Heat Pump Simultaneous - COP"]

    # Drop rows with any NaN values
    input_train_HP_sim = input_train_HP_sim.dropna()
    target_train_HP_sim = target_train_HP_sim.dropna()
    input_pred_HP_sim = key_outputs[
        [
            "Heat Pump Simultaneous - Cold EWT",
            "Heat Pump Simultaneous - Cold LWT",
            "Heat Pump Simultaneous - Hot EWT",
            "Heat Pump Simultaneous - Hot LWT",
        ]
    ]

    newCUp_reg_df["Heat Pump Simultaneous - COP"] = newCUp_reg(
        input_train_HP_sim, target_train_HP_sim, input_pred_HP_sim
    )

    ## HP COP -H- Air source ##

    # Rename columns in key_outputs to match those in calculation_map_newCUP_regData
    key_outputs = key_outputs.rename(
        columns={
            "HP_H-AirS-Ambient (F)": "Ambient Temperature (°F)",
            "HP_H-AirS-HHW Entering (F)": "Heat Pump Heating Only Air-Source - Hot EWT",
            "HP_H-AirS-HHW Leaving (F)": "Heat Pump Heating Only Air-Source - Hot LWT",
        }
    )

    input_train_HP_H_AS = calculation_map_newCUP_regData[
        [
            "Ambient Temperature (°F)",
            "Heat Pump Heating Only Air-Source - Hot EWT",
            "Heat Pump Heating Only Air-Source - Hot LWT",
        ]
    ]
    target_train_HP_H_AS = calculation_map_newCUP_regData["Heat Pump Heating Only Air-Source - COP"]

    # Drop rows with any NaN values
    input_train_HP_H_AS = input_train_HP_H_AS.dropna()
    target_train_HP_H_AS = target_train_HP_H_AS.dropna()
    input_pred_HP_H_AS = key_outputs[
        [
            "Ambient Temperature (°F)",
            "Heat Pump Heating Only Air-Source - Hot EWT",
            "Heat Pump Heating Only Air-Source - Hot LWT",
        ]
    ]

    newCUp_reg_df["Heat Pump Heating Only Air-Source - COP"] = newCUp_reg(
        input_train_HP_H_AS, target_train_HP_H_AS, input_pred_HP_H_AS
    )

    ## HP COP -H- Water source ##

    # Rename columns in key_outputs to match those in calculation_map_newCUP_regData
    key_outputs = key_outputs.rename(
        columns={
            "HP_H-GrS-Water-Source Leaving (F)": "Heat Pump Heating Only Water-Source - SSEWT-1",
            "HP_H-OcS-Water-Source Leaving (F)": "Heat Pump Heating Only Water-Source - SSEWT-2",
            "HP_H-GrS-Water-Source Entering (F)": "Heat Pump Heating Only Water-Source - SSLWT-1",
            "HP_H-OcS-Water-Source Entering (F)": "Heat Pump Heating Only Water-Source - SSLWT-2",
            "HP_H-GrS-HHW Entering (F)": "Heat Pump Heating Only Water-Source - Hot EWT-1",
            "HP_H-OcS-HHW Entering (F)": "Heat Pump Heating Only Water-Source - Hot EWT-2",
            "HP_H-GrS-HHW Leaving (F)": "Heat Pump Heating Only Water-Source - Hot LWT-1",
            "HP_H-OcS-HHW Leaving (F)": "Heat Pump Heating Only Water-Source - Hot LWT-2",
        }
    )

    input_train_HP_H_WS = calculation_map_newCUP_regData[
        [
            "Heat Pump Heating Only Water-Source - SSEWT-1",
            "Heat Pump Heating Only Water-Source - SSEWT-2",
            "Heat Pump Heating Only Water-Source - SSLWT-1",
            "Heat Pump Heating Only Water-Source - SSLWT-2",
            "Heat Pump Heating Only Water-Source - Hot EWT-1",
            "Heat Pump Heating Only Water-Source - Hot EWT-2",
            "Heat Pump Heating Only Water-Source - Hot LWT-1",
            "Heat Pump Heating Only Water-Source - Hot LWT-2",
        ]
    ]
    target_train_HP_H_WS = calculation_map_newCUP_regData["Heat Pump Heating Only Water-Source - COP"]

    # Drop rows with any NaN values
    input_train_HP_H_WS = input_train_HP_H_WS.dropna()
    target_train_HP_H_WS = target_train_HP_H_WS.dropna()
    input_pred_HP_H_WS = key_outputs[
        [
            "Heat Pump Heating Only Water-Source - SSEWT-1",
            "Heat Pump Heating Only Water-Source - SSEWT-2",
            "Heat Pump Heating Only Water-Source - SSLWT-1",
            "Heat Pump Heating Only Water-Source - SSLWT-2",
            "Heat Pump Heating Only Water-Source - Hot EWT-1",
            "Heat Pump Heating Only Water-Source - Hot EWT-2",
            "Heat Pump Heating Only Water-Source - Hot LWT-1",
            "Heat Pump Heating Only Water-Source - Hot LWT-2",
        ]
    ]

    newCUp_reg_df["Heat Pump Heating Only Water-Source - COP"] = newCUp_reg(
        input_train_HP_H_WS, target_train_HP_H_WS, input_pred_HP_H_WS
    )

    ## HP COP -C- Air source ##

    # Rename columns in key_outputs to match those in calculation_map_newCUP_regData
    key_outputs = key_outputs.rename(
        columns={
            "HP_C-AirS-Ambient (F)": "Ambient Temperature (°F)-2",
            "HP_C-AirS-CHW Entering (F)": "Heat Pump Cooling Only Air-Source - Cold EWT",
            "HP_C-AirS-CHW Leaving (F)": "Heat Pump Cooling Only Air-Source - Cold LWT",
        }
    )

    input_train_HP_C_AS = calculation_map_newCUP_regData[
        [
            "Ambient Temperature (°F)-2",
            "Heat Pump Cooling Only Air-Source - Cold EWT",
            "Heat Pump Cooling Only Air-Source - Cold LWT",
        ]
    ]
    target_train_HP_C_AS = calculation_map_newCUP_regData["Heat Pump Cooling Only Air-Source - COP"]

    # Drop rows with any NaN values
    input_train_HP_C_AS = input_train_HP_C_AS.dropna()
    target_train_HP_C_AS = target_train_HP_C_AS.dropna()
    input_pred_HP_C_AS = key_outputs[
        [
            "Ambient Temperature (°F)-2",
            "Heat Pump Cooling Only Air-Source - Cold EWT",
            "Heat Pump Cooling Only Air-Source - Cold LWT",
        ]
    ]

    newCUp_reg_df["Heat Pump Cooling Only Air-Source - COP"] = newCUp_reg(
        input_train_HP_C_AS, target_train_HP_C_AS, input_pred_HP_C_AS
    )

    ## HP COP -C- Water source ##

    # Rename columns in key_outputs to match those in calculation_map_newCUP_regData
    key_outputs = key_outputs.rename(
        columns={
            "HP_C-GrS-Water-Source Leaving (F)": "Heat Pump Cooling Only Water-Source - SSEWT-1",
            "HP_C-OcS-Water-Source Leaving (F)": "Heat Pump Cooling Only Water-Source - SSEWT-2",
            "HP_C-TS-Water-Source Leaving (F)": "Heat Pump Cooling Only Water-Source - SSEWT-3",
            "HP_C-GrS-Water-Source Entering (F)": "Heat Pump Cooling Only Water-Source - SSLWT-1",
            "HP_C-OcS-Water-Source Entering (F)": "Heat Pump Cooling Only Water-Source - SSLWT-2",
            "HP_C-TS-Water-Source Entering (F)": "Heat Pump Cooling Only Water-Source - SSLWT-3",
            "HP_C-GrS-CHW Entering (F)": "Heat Pump Cooling Only Water-Source - Cold EWT-1",
            "HP_C-OcS-CHW Entering (F)": "Heat Pump Cooling Only Water-Source - Cold EWT-2",
            "HP_C-TS-CHW Entering (F)": "Heat Pump Cooling Only Water-Source - Cold EWT-3",
            "HP_C-GrS-CHW Leaving (F)": "Heat Pump Cooling Only Water-Source - Cold LWT-1",
            "HP_C-OcS-CHW Leaving (F)": "Heat Pump Cooling Only Water-Source - Cold LWT-2",
            "HP_C-TS-CHW Leaving (F)": "Heat Pump Cooling Only Water-Source - Cold LWT-3",
        }
    )

    input_train_HP_C_WS = calculation_map_newCUP_regData[
        [
            "Heat Pump Cooling Only Water-Source - SSEWT-1",
            "Heat Pump Cooling Only Water-Source - SSEWT-2",
            "Heat Pump Cooling Only Water-Source - SSEWT-3",
            "Heat Pump Cooling Only Water-Source - SSLWT-1",
            "Heat Pump Cooling Only Water-Source - SSLWT-2",
            "Heat Pump Cooling Only Water-Source - SSLWT-3",
            "Heat Pump Cooling Only Water-Source - Cold EWT-1",
            "Heat Pump Cooling Only Water-Source - Cold EWT-2",
            "Heat Pump Cooling Only Water-Source - Cold EWT-3",
            "Heat Pump Cooling Only Water-Source - Cold LWT-1",
            "Heat Pump Cooling Only Water-Source - Cold LWT-2",
            "Heat Pump Cooling Only Water-Source - Cold LWT-3",
        ]
    ]
    target_train_HP_C_WS = calculation_map_newCUP_regData["Heat Pump Cooling Only Water-Source - COP"]

    # Drop rows with any NaN values
    input_train_HP_C_WS = input_train_HP_C_WS.dropna()
    target_train_HP_C_WS = target_train_HP_C_WS.dropna()
    # print("input_pred_HP_C_WS",key_outputs["HP_C-GrS-CHW Leaving (F)"])
    input_pred_HP_C_WS = key_outputs[
        [
            "Heat Pump Cooling Only Water-Source - SSEWT-1",
            "Heat Pump Cooling Only Water-Source - SSEWT-2",
            "Heat Pump Cooling Only Water-Source - SSEWT-3",
            "Heat Pump Cooling Only Water-Source - SSLWT-1",
            "Heat Pump Cooling Only Water-Source - SSLWT-2",
            "Heat Pump Cooling Only Water-Source - SSLWT-3",
            "Heat Pump Cooling Only Water-Source - Cold EWT-1",
            "Heat Pump Cooling Only Water-Source - Cold EWT-2",
            "Heat Pump Cooling Only Water-Source - Cold EWT-3",
            "Heat Pump Cooling Only Water-Source - Cold LWT-1",
            "Heat Pump Cooling Only Water-Source - Cold LWT-2",
            "Heat Pump Cooling Only Water-Source - Cold LWT-3",
        ]
    ]

    newCUp_reg_df["Heat Pump Cooling Only Water-Source - COP"] = newCUp_reg(
        input_train_HP_C_WS, target_train_HP_C_WS, input_pred_HP_C_WS
    )

    newCUp_reg_df["Electric Boiler - COP"] = [
        calculation_map_newCUP_regData["Electric Boiler Data Columns with corresponding COP"][0]
    ] * 8760

################## New CUP Elec Use ###########################

if year == 2025:
    new_CUP_equip_elec_Use = pd.DataFrame()

else:
    # repeat COP as per number of bldgs
    def cop_column_tiled(
        rounded_dryBulb_temps,
        dry_bulb_temps,
        COP_newBldgEquip_reg_output,
        column,
        loads_len,
    ):
        # Find the index of the closest wet bulb temperature for each weather temperature
        closest_indices_2 = np.abs(dry_bulb_temps.values[:, None] - rounded_dryBulb_temps.values).argmin(axis=0)

        # Use the closest indices to retrieve corresponding COP values
        assigned_cooling_cop_values = COP_newBldgEquip_reg_output[column].iloc[closest_indices_2].reset_index(drop=True)

        # Determine the length of each segment (8760)
        segment_length = len(assigned_cooling_cop_values)

        # Calculate the number of complete cycles
        num_cycles = loads_len // segment_length

        # Repeat COP values to match the length of load values
        cop_repeated = np.tile(assigned_cooling_cop_values, num_cycles)

        return cop_repeated

    new_CUP_equip_elec_Use = pd.DataFrame()
    # assiging cooling COP
    # new_bldg_equip_elec_Use["Current New Bldg Cooling COP_DB"] = cop_column(rounded_dryBulb_temps,dry_bulb_temps,COP_newBldgEquip_reg_output,"New Building Independent Heat Pump - Cooling COP (44°F CHWST)",new_Bldg_Therm_Op_Loads.shape[0])

    # elec boiler load to usage
    new_CUP_equip_elec_Use["New CUP Electric Boiler Electricity Use (kWh)"] = (
        key_outputs_OG["Boiler-HHW Load (btu)"] / newCUp_reg_df["Electric Boiler - COP"]
    )

    new_CUP_equip_elec_Use["New CUP Chiller Electricity Use (kWh)"] = (
        key_outputs_OG["Chiller-GrS-CHW Load (btu)"] / newCUp_reg_df["Chiller COP"]
        + key_outputs_OG["Chiller-OcS-CHW Load (btu)"] / newCUp_reg_df["Chiller COP"]
        + key_outputs_OG["Chiller-TS-CHW Load (btu)"] / newCUp_reg_df["Chiller COP"]
    )

    new_CUP_equip_elec_Use["New CUP Heat Pump in Simultaneous Electricity Use (kWh)"] = (
        key_outputs_OG["HP_HC-HHW Load (btu)"] / newCUp_reg_df["Heat Pump Simultaneous - COP"]
    )

    new_CUP_equip_elec_Use["New CUP Heat Pump in Heating Only with Air-Source Electricity Use (kWh)"] = (
        key_outputs_OG["HP_H-AirS-HHW Load (btu)"] / newCUp_reg_df["Heat Pump Heating Only Air-Source - COP"]
    )

    new_CUP_equip_elec_Use["New CUP Heat Pump in Heating Only with Water-Source Electricity Use (kWh)"] = (
        key_outputs_OG["HP_H-GrS-HHW Load (btu)"] / newCUp_reg_df["Heat Pump Heating Only Water-Source - COP"]
        + key_outputs_OG["HP_H-OcS-HHW Load (btu)"] / newCUp_reg_df["Heat Pump Heating Only Water-Source - COP"]
    )

    new_CUP_equip_elec_Use["New CUP Heat Pump in Cooling Only with Air-Source Electricity Use (kWh)"] = (
        key_outputs_OG["HP_C-AirS-CHW Load (btu)"] / newCUp_reg_df["Heat Pump Cooling Only Air-Source - COP"]
    )

    new_CUP_equip_elec_Use["New CUP Heat Pump in Cooling Only with Water-Source Electricity Use (kWh)"] = (
        key_outputs_OG["HP_C-GrS-CHW Load (btu)"] / newCUp_reg_df["Heat Pump Cooling Only Water-Source - COP"]
        + key_outputs_OG["HP_C-OcS-CHW Load (btu)"] / newCUp_reg_df["Heat Pump Cooling Only Water-Source - COP"]
        + key_outputs_OG["HP_C-TS-CHW Load (btu)"] / newCUp_reg_df["Heat Pump Cooling Only Water-Source - COP"]
    )


################  Building Total Electricity Use ###########

df1_E_CAAN = pd.DataFrame()
df4_E_CAAN = pd.DataFrame()

df1_E = pd.DataFrame(current_District_Elec_Use["Current District System Cooling Electricity Use (kWh)"])

df1_E_CAAN["Building ID CAAN"] = ["current_District_Elec_Use"] * len(df1_E)

df2_E_CAAN = Current_Bldg_Equip_Elec_Use[
    [
        "Building ID CAAN",
        "Current Building Equipment Heating Electricity Use (kWh)",
        "Current Building Equipment Hot Water Electricity Use (kWh)",
        "Current Building Equipment Cooking Electricity Use (kWh)",
        "Current Building Equipment Laundry Electricity Use (kWh)",
        "Current Building Equipment Other Process Electricity Use (kWh)",
        "Current Building Equipment Cooling Electricity Use (kWh)",
    ]
]
df3_E_CAAN = new_bldg_equip_elec_Use[
    [
        "Building ID CAAN",
        "New Building Independent Heat Pump Cooling Electricity Use",
        "New Building Independent Heat Pump Heating Electricity Use (kWh)",
        "New Building Independent Heat Pump Hot Water Electricity Use (kWh)",
        "New Building Equipment Cooking Electricity Use (kWh)",
        "New Building Equipment Laundry Electricity Use (kWh)",
    ]
]
df4_E = new_CUP_equip_elec_Use
df4_E_CAAN["Building ID CAAN"] = ["new_CUP_equip_elec_Use"] * len(df4_E)
df5_E = allBldgElecUse_output[
    [
        "Building ID CAAN",
        "Plug Loads (kWh)",
        "Lighting (kWh)",
        "Fans (kWh)",
        "Pumps (kWh)",
    ]
]


# Specify the columns to update conditionally
columns_to_update = ["Plug Loads (kWh)", "Lighting (kWh)", "Fans (kWh)", "Pumps (kWh)"]

# Filter df5_E to include only rows with common Building ID CAAN
filtered_df5_E_2 = df5_E[df5_E["Building ID CAAN"].isin(df2_E_CAAN["Building ID CAAN"])]

# Filter df5_E to include only rows with common Building ID CAAN
filtered_df5_E_3 = df5_E[df5_E["Building ID CAAN"].isin(df3_E_CAAN["Building ID CAAN"])]


# Create the columns in df3_E_CAAN if they do not exist
for col in columns_to_update:
    df2_E_CAAN[col] = 0
    df3_E_CAAN[col] = 0  # Initialize columns with 0

# Use np.where to conditionally update values in df3_E_CAAN
for col in columns_to_update:
    if not df2_E_CAAN.empty:
        df2_E_CAAN[col] = np.where(
            df2_E_CAAN["Building ID CAAN"].isin(filtered_df5_E_2["Building ID CAAN"]),
            filtered_df5_E_2[col],
            df2_E_CAAN[col],
        )
    if not df3_E_CAAN.empty:
        df3_E_CAAN[col] = np.where(
            df3_E_CAAN["Building ID CAAN"].isin(filtered_df5_E_3["Building ID CAAN"]),
            filtered_df5_E_3[col],
            df3_E_CAAN[col],
        )


# Concatenate the DataFrames along rows (vertically)
CAAN_df = pd.concat(
    [
        df1_E_CAAN["Building ID CAAN"],
        df2_E_CAAN["Building ID CAAN"],
        df3_E_CAAN["Building ID CAAN"],
        df4_E_CAAN["Building ID CAAN"],
    ],
    axis=0,
    ignore_index=True,
)


# Specify axis=1 for column, inplace=True to modify df in-place
df2_E = df2_E_CAAN[
    [
        "Current Building Equipment Heating Electricity Use (kWh)",
        "Current Building Equipment Hot Water Electricity Use (kWh)",
        "Current Building Equipment Cooking Electricity Use (kWh)",
        "Current Building Equipment Laundry Electricity Use (kWh)",
        "Current Building Equipment Other Process Electricity Use (kWh)",
        "Current Building Equipment Cooling Electricity Use (kWh)",
        "Plug Loads (kWh)",
        "Lighting (kWh)",
        "Fans (kWh)",
        "Pumps (kWh)",
    ]
]
df3_E = df3_E_CAAN[
    [
        "New Building Independent Heat Pump Cooling Electricity Use",
        "New Building Independent Heat Pump Heating Electricity Use (kWh)",
        "New Building Independent Heat Pump Hot Water Electricity Use (kWh)",
        "New Building Equipment Cooking Electricity Use (kWh)",
        "New Building Equipment Laundry Electricity Use (kWh)",
        "Plug Loads (kWh)",
        "Lighting (kWh)",
        "Fans (kWh)",
        "Pumps (kWh)",
    ]
]

df1_E = df1_E.fillna(0) if df1_E is not None else pd.DataFrame()
df2_E = df2_E.fillna(0) if df2_E is not None else pd.DataFrame()
df3_E = df3_E.fillna(0) if df3_E is not None else pd.DataFrame()
df4_E = df4_E.fillna(0) if df4_E is not None else pd.DataFrame()


# List of DataFrames and corresponding names
dfs_elec = [df1_E, df2_E, df3_E, df4_E]
df_names_elec = [
    "current_District_Elec_Use",
    "Current_Bldg_Equip_Elec_Use",
    "new_bldg_equip_elec_Use",
    "new_CUP_equip_elec_Use",
]

# Initialize an empty list to store DataFrame summaries
result_data_elec = []
result_data_gas = []


def sum_usage(dfs, df_names, result_data):
    # Iterate over each DataFrame and its name
    for df, name in zip(dfs, df_names):
        # Calculate row-wise sums
        if df.empty:
            df["Sum"] = 0
        #  print(f"DataFrame {name} is empty")
        elif len(df.columns) > 1:
            df["Sum"] = df.sum(axis=1)
        elif len(df.columns) == 1:
            df["Sum"] = df.iloc[:, 0]  # Use the single column as the 'Sum'

        # Add DataFrame name as a new column
        df["DataFrame"] = name

        # Select columns of interest and append to result_data
        result_data.append(df[["Sum", "DataFrame"]])

    # Concatenate all DataFrame summaries into a single DataFrame
    summed_results = pd.concat(result_data, ignore_index=True)
    return summed_results


bldg_total_elec_use = sum_usage(dfs_elec, df_names_elec, result_data_elec)
bldg_total_elec_use["Building ID CAAN"] = CAAN_df
num_repeats = len(bldg_total_elec_use) // 8760
# Create a new column with the repeated series
bldg_total_elec_use["Timestamp"] = np.tile(dateTime.values, num_repeats)


############# Total Gas #########

df1_G_CAAN = pd.DataFrame()


df1_G = current_District_Gas_Use
df1_G_CAAN["Building ID CAAN"] = ["current_District_Gas_Use"] * len(df1_G)
df2_G = Current_Bldg_Equip_Gas_Use[
    [
        "Current Building Equipment Heating Gas Use (therms)",
        "Current Building Equipment Hot Water Gas Use (therms)",
        "Current Building Equipment Cooking Gas Use (therms)",
        "Current Building Equipment Laundry Gas Use (therms)",
    ]
]
df2_G_CAAN = Current_Bldg_Equip_Gas_Use[["Building ID CAAN", "Current Building Equipment Heating Gas Use (therms)"]]
df3_G = pd.DataFrame(allBldgGasUse_output["Other Process (Therms)"])
df3_G_CAAN = allBldgGasUse_output[["Building ID CAAN", "Other Process (Therms)"]]


# Concatenate the DataFrames along rows (vertically)
CAAN_G_df = pd.concat(
    [
        df1_G_CAAN["Building ID CAAN"],
        df2_G_CAAN["Building ID CAAN"],
        df3_G_CAAN["Building ID CAAN"],
    ],
    axis=0,
    ignore_index=True,
)


df1_G_filled = df1_G.fillna(0)
df2_G_filled = df2_G.fillna(0)
df3_G_filled = df3_G.fillna(0)


# List of DataFrames and corresponding names for gas
dfs_gas = [
    df1_G_filled,
    df2_G_filled,
    df3_G_filled,
]
# Simulations Gas Use is allBldgGasUse_output below
df_names_gas = [
    "current_District_Gas_Use",
    "Current_Bldg_Equip_Gas_Use",
    "Simulations Gas Use",
]

bldg_total_gas_use = sum_usage(dfs_gas, df_names_gas, result_data_gas)

bldg_total_gas_use["Building ID CAAN"] = CAAN_G_df

num_repeats = len(bldg_total_gas_use) // 8760
# Create a new column with the repeated series
bldg_total_gas_use["Timestamp"] = np.tile(dateTime.values, num_repeats)


######### Net Elec Use by Billing Group ###############

# Step 1: Merge DataFrames on 'Building ID CAAN' to include 'Billing Group Number'
elec_billing_df = pd.merge(
    bldg_total_elec_use,
    building_meta_df[
        [
            "Building ID CAAN",
            "Electric Utility Billing Group",
            "Electricity Utility Provider",
        ]
    ],
    on="Building ID CAAN",
    how="left",
)
elec_billing_df["Electric Utility Billing Group"] = elec_billing_df["Electric Utility Billing Group"].fillna(
    "UCOP Main"
)
elec_billing_df["Electricity Utility Provider"] = elec_billing_df["Electricity Utility Provider"].fillna("UCOP")

# Step 2: Group by 'Billing Group Number' and 'Timestamp', then aggregate 'Building Usage'
bldg_total_elec_grouped_df = (
    elec_billing_df.groupby(["Electric Utility Billing Group", "Timestamp", "Electricity Utility Provider"])["Sum"]
    .sum()
    .reset_index()
)

########### Elec Cost by Billing Group  ###########

elec_data_excel = pd.read_excel("UCSB Calculation Map.xlsx", sheet_name="Electric Rates by Utility Prov", header=1)


timestamp = elec_data_excel["Timestamp"]
provider = elec_data_excel["Electricity Utility Provider"]
rates = elec_data_excel["Base Electricity Rate ($/kWh)"]
rates_df = pd.DataFrame()
rates_df["Electricity Utility Provider"] = provider
rates_df["Timestamp"] = timestamp
rates_df["Rates"] = rates
rates_df["Escalation Rate (%)"] = elec_data_excel["Escalation Rate (%)"]
rates_df = rates_df.reset_index()


# # Create a dictionary mapping provider names to their respective rate values
# rate_mapping = dict(zip(rates_df['Electricity Utility Provider'], rates_df['Rates']))

# # Create a dictionary mapping (provider, timestamp) to rate value
# rate_mapping = {(row['Electricity Utility Provider'], row['Timestamp']): row['Rates']
#                 for index, row in rates_df.iterrows()}

# # Function to map rate values based on provider and timestamp
# def map_rates(row):
#     provider = row['Electricity Utility Provider']
#     timestamp = row['Timestamp']
#     return rate_mapping.get((provider, timestamp), None)  # Get rate value from mapping dictionary


# Create a dictionary mapping (provider, timestamp) to a tuple of (base rate, escalation rate)
rate_mapping = {
    (row["Electricity Utility Provider"], row["Timestamp"]): (
        row["Rates"],
        row["Escalation Rate (%)"],
    )
    for index, row in rates_df.iterrows()
}


# Function to map rate values based on provider and timestamp
def map_rates(row: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    provider = row["Electricity Utility Provider"]
    timestamp = row["Timestamp"]
    if (provider, timestamp) in rate_mapping:
        base_rate, escalation_rate = rate_mapping[(provider, timestamp)]
        return (
            base_rate,
            escalation_rate,
        )  # Return tuple of base rate and escalation rate
    else:
        return None, None


# Apply the mapping function to create new columns 'Mapped Base Rate' and 'Mapped Escalation Rate'
(
    bldg_total_elec_grouped_df["Mapped Base Rate"],
    bldg_total_elec_grouped_df["Mapped Escalation Rate"],
) = zip(*bldg_total_elec_grouped_df.apply(map_rates, axis=1))
bldg_total_elec_grouped_df["Mapped Escalation Rate"] = bldg_total_elec_grouped_df["Mapped Escalation Rate"].fillna(0)

year_difference = year - base_year

bldg_total_elec_grouped_df["Base Electricity Cost ($)"] = (
    bldg_total_elec_grouped_df["Sum"]
    * bldg_total_elec_grouped_df["Mapped Base Rate"]
    * (1 + bldg_total_elec_grouped_df["Mapped Escalation Rate"]) ** year_difference
)


################################ Gas structure on hold for now ##############################

######### Net Gas Use by Billing Group ###############


# gas_data_excel = pd.read_excel("UCSB Calculation Map.xlsx",sheet_name="Gas Rates by Utility Provider",header =1)


# # Step 1: Merge DataFrames on 'Building ID CAAN' to include 'Billing Group Number'
# gas_billing_df = pd.merge(bldg_total_gas_use, building_meta_df[['Building ID CAAN', 'Gas Utility Billing Group',"Gas Utility Provider"]], on='Building ID CAAN', how='left')
# gas_billing_df["Gas Utility Billing Group"] = gas_billing_df["Gas Utility Billing Group"].fillna("DGS")
# gas_billing_df["Gas Utility Provider"] = gas_billing_df["Gas Utility Provider"].fillna("DGS")

# # Step 2: Group by 'Billing Group Number' and 'Timestamp', then aggregate 'Building Usage'
# bldg_total_gas_grouped_df = gas_billing_df.groupby(['Gas Utility Billing Group', 'Timestamp',"Gas Utility Provider"])['Sum'].sum().reset_index()


# rates_df_gas = pd.DataFrame()
# rates_df_gas["Gas Utility Provider"]=gas_data_excel['Gas Utility Provider']
# rates_df_gas["Timestamp"]=gas_data_excel['Timestamp']
# rates_df_gas["Rates"]=gas_data_excel['Gas Rate ($/therms)']


# # Create a dictionary mapping (provider, timestamp) to rate value
# rate_mapping_gas = {(row['Gas Utility Provider'], row['Timestamp']): row['Rates']
#                 for index, row in rates_df_gas.iterrows()}


# # Function to map rate values based on provider and timestamp
# def map_rates_gas(row):
#     provider = row['Gas Utility Provider']
#     timestamp = row['Timestamp']
#     return rate_mapping.get((provider, timestamp), None)  # Get rate value from mapping dictionary


# # Apply the mapping function to create new columns 'Mapped Base Rate' and 'Mapped Escalation Rate'
# bldg_total_gas_grouped_df['Mapped Base Rate']= bldg_total_gas_grouped_df.apply(map_rates_gas, axis=1)
