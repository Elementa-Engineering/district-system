import math

import numpy as np
import pandas as pd

# import all the sheets from the inputs excel file
inputs_sheetDict = pd.read_excel("Inputs.xlsx", sheet_name=None)

# Access individual sheets as dataframes from the dictionary
CUP_inputs_df = inputs_sheetDict["Sheet1"]
building_inputs_df = inputs_sheetDict["Sheet2"]
TES_inputs_df = inputs_sheetDict["Sheet3"]
hotTank_schedule1_inputs_df = inputs_sheetDict["Sheet4"]
coldTank_schedule2_inputs_df = inputs_sheetDict["Sheet5"]
hotWater_schedule3_inputs_df = inputs_sheetDict["Sheet6"]
domesticWater_schedule4_inputs_df = inputs_sheetDict["Sheet7"]
chilledCTOcean_schedule5_inputs_df = inputs_sheetDict["Sheet8"]
groundReturn_schedule6_inputs_df = inputs_sheetDict["Sheet9"]


###############calculating formulas in df before dict##############################

## Adding formulas for groundReturn_schedule6_inputs_df
# Apply the formula to calculate 'Ht Ex - EWT' column
groundReturn_schedule6_inputs_df["Ht Ex - EWT"] = groundReturn_schedule6_inputs_df["Ht Ex - LWT*"].apply(
    lambda x: x - 10 if not pd.isna(x) else float("nan")
)
# Apply the formula to calculate 'Ht Ex - EWT' column
groundReturn_schedule6_inputs_df["Ht Rej - EWT"] = groundReturn_schedule6_inputs_df["Ht Rej - LWT*"].apply(
    lambda x: 10 + x if not pd.isna(x) else float("nan")
)


##Adding formulas for Tank_schedule1_inputs_df
# Sum the values of the columns from index 1 to 23 (corresponding to hours 0 to 23)
# hot tank
hotTank_schedule1_inputs_df["Total"] = hotTank_schedule1_inputs_df.loc[:, 0:23].sum(axis=1)
hotTank_schedule1_inputs_df.head(15)
# cold tank
coldTank_schedule2_inputs_df["Total"] = coldTank_schedule2_inputs_df.loc[:, 0:23].sum(axis=1)
coldTank_schedule2_inputs_df.head(15)


###############converting df to dictionary##############################

# the function to changes input dataframe to dictionaries(single value input)


def createDict(df):
    # Initialize an empty dictionary to store the data
    data_dict = {}

    # Filter out rows with NaN category (if any)
    df = df.dropna(subset=[df.columns[1]])

    # Group by category and create nested dictionaries using pandas groupby
    grouped = df.groupby(df.columns[1])

    for category, group_df in grouped:
        data_dict[category] = dict(zip(group_df.iloc[:, 2], group_df.iloc[:, 3]))

    return data_dict


# single input value dicts
CUP_inputs = createDict(CUP_inputs_df)
building_inputs = createDict(building_inputs_df)
TES_inputs = createDict(TES_inputs_df)
domesticWater_sch4_inputs = createDict(domesticWater_schedule4_inputs_df)
chilledCTOcean_sch5_inputs = createDict(chilledCTOcean_schedule5_inputs_df)


# the function to changes input dataframe to dictionaries(multiple value input)


def createDict_multipleValues(df):
    # Initialize an empty dictionary to store the data
    data_dict = {}

    # Filter out rows with NaN category (if any)
    df = df.dropna(subset=[df.columns[1]])

    # Group by category and create nested dictionaries using pandas groupby
    grouped = df.groupby(df.columns[1])

    for category, group_df in grouped:
        # Initialize a nested dictionary for the current category
        category_dict = {}

        for _, row in group_df.iloc[:, 2:].iterrows():
            month = row[group_df.columns[2]]
            if month not in category_dict:
                category_dict[month] = {}
            for hour_column, value in row.items():
                # Skip if the column name is the month column or NaN value
                if hour_column == group_df.columns[2]:
                    continue

                # Extract the hour (column name as integer)
                hour = hour_column

                #                 # Create a compound key using month and hour
                #                 key = (month, hour)

                category_dict[month][hour] = value
        # Add the category dictionary to the main data dictionary
        data_dict[category] = category_dict
    return data_dict


hotTank_sch1_inputs = createDict_multipleValues(hotTank_schedule1_inputs_df)
coldTank_sch2_inputs = createDict_multipleValues(coldTank_schedule2_inputs_df)
hotWater_sch3_inputs = createDict_multipleValues(hotWater_schedule3_inputs_df)
groundReturn_sch6_inputs = createDict_multipleValues(groundReturn_schedule6_inputs_df)

###############calculating the inputs###############


def calculate_inputs(
    CUP_inputs,
    building_inputs,
    TES_inputs,
    hotWater_schedule3_inputs_df,
    chilledCTOcean_schedule5_inputs_df,
):
    # CUP setpoints
    maxValue_hotWater = hotWater_schedule3_inputs_df["CUP"].max()
    CUP_inputs["Setpoints"]["Hot Water Supply"] = maxValue_hotWater
    maxValue_chilledWater = chilledCTOcean_schedule5_inputs_df.loc[
        chilledCTOcean_schedule5_inputs_df["Schedules Category"] == "Chilled Water Setpoint",
        "CUP",
    ].max()
    CUP_inputs["Setpoints"]["Chilled Water Supply"] = maxValue_chilledWater

    # CUP electric chillers
    CUP_inputs["Electric Chillers"]["Capacity for Min Lift"] = CUP_inputs["Electric Chillers"]["Max Capacity"] * 0.3

    # #building Chilled water
    # maxValue_cooling = buildingUsage_df['Cooling Load (Btu/h)'].max()
    # building_inputs["Chilled Water"]["Max Load"]= maxValue_cooling

    # #building DHW
    # maxValue_DHW = buildingUsage_df['DHW Load (Btu/h)'].max()
    # building_inputs["Domestic Hot Water"]["Max Load"]= maxValue_DHW
    # building_inputs["Domestic Hot Water"]["Load @ Min Approach"]= maxValue_DHW*0.26

    # #building HHW
    # maxValue_HHW = buildingUsage_df['Heating Load (Btu/h)'].max()
    # building_inputs["Heating Hot Water"]["Max Load"]= maxValue_HHW + building_inputs["Domestic Hot Water"]["Max Load"]

    # TES Tank Tank Properties
    CUFtoGAL = TES_inputs["Conversion Rates"]["CUF to GAL"]
    hot_radius = TES_inputs["Tank Properties"]["TES Hot Diameter"] / 2
    hot_height = TES_inputs["Tank Properties"]["TES Hot Height"]
    TES_inputs["Tank Properties"]["TES Hot Tank Volume"] = math.pi * (hot_radius**2) * hot_height * CUFtoGAL

    cold_radius = TES_inputs["Tank Properties"]["TES Cold Diameter"] / 2
    cold_height = TES_inputs["Tank Properties"]["TES Cold Height"]
    TES_inputs["Tank Properties"]["TES Cold Tank Volume"] = math.pi * (cold_radius**2) * cold_height * CUFtoGAL

    # TES Initial Conditions
    # TES Hot Tank Upper Tank Volume ----- Check the condition and calculate the result accordingly
    hot_volume1 = TES_inputs["Tank Properties"]["TES Hot Tank Volume"]
    hot_volume2 = (
        TES_inputs["Initial Conditions"]["TES Hot Thermocline thickness"] * math.pi * (hot_radius**2) * CUFtoGAL
    )  # Volume of second part of the cylinder
    difference = hot_volume1 - hot_volume2  # Difference between the volumes
    TES_inputs["Initial Conditions"]["TES Hot Tank Upper Tank Volume"] = (
        difference * TES_inputs["Initial Conditions"]["Starting TES Hot Charge"]
    )
    TESHotUpperTankVolume = TES_inputs["Initial Conditions"]["TES Hot Tank Upper Tank Volume"]

    # TES Hot Thermocline volume
    TES_inputs["Initial Conditions"]["TES Hot Thermocline volume"] = hot_volume2

    # TES Hot Tank Lower Tank Volume
    TES_inputs["Initial Conditions"]["TES Hot Tank Lower Tank Volume"] = (
        hot_volume1 - hot_volume2 - TESHotUpperTankVolume
    )

    # TES Cold Tank Lower Tank Volume ----- Check the condition and calculate the result accordingly
    cold_volume1 = TES_inputs["Tank Properties"]["TES Cold Tank Volume"]
    cold_volume2 = (
        TES_inputs["Initial Conditions"]["TES Cold Thermocline thickness"] * math.pi * (cold_radius**2) * CUFtoGAL
    )  # Volume of second part of the cylinder
    difference = cold_volume1 - cold_volume2  # Difference between the volumes
    TES_inputs["Initial Conditions"]["TES Cold Tank Lower Tank Volume"] = (
        difference * TES_inputs["Initial Conditions"]["Starting TES Cold Charge"]
    )
    TESColdLowerTankVolume = TES_inputs["Initial Conditions"]["TES Cold Tank Lower Tank Volume"]
    # TES cold Thermocline volume
    TES_inputs["Initial Conditions"]["TES Cold Thermocline volume"] = cold_volume2
    # TES Hot Tank Lower Tank Volume
    TES_inputs["Initial Conditions"]["TES Cold Tank Upper Tank Volume"] = (
        cold_volume1 - cold_volume2 - TESColdLowerTankVolume
    )

    # Tank Charging Characteristics
    # TES Hot Capacity
    GALtoLbs = TES_inputs["Conversion Rates"]["GAL to Lbs"]
    upperHotTemp = TES_inputs["Initial Conditions"]["TES Hot Tank Upper Tank Temp"]
    lowerHotTemp = TES_inputs["Initial Conditions"]["TES Hot Tank Lower Tank Temp"]
    TES_inputs["Tank Charging Characteristics"]["TES Hot Capacity"] = (
        GALtoLbs * (upperHotTemp - lowerHotTemp) * hot_volume1 / 1000
    )
    # TES Hot Max Flow
    tankVolumeMoved = TES_inputs["Tank Charging Characteristics"]["TES Hot Max % of Total Tank Volume moved in 1 hr"]
    TES_inputs["Tank Charging Characteristics"]["TES Hot Max Flow"] = (
        math.ceil((hot_volume1 * tankVolumeMoved) / 60 / 5) * 5
    )
    # TES Hot Max Flow
    hot_tankVolumeMoved = TES_inputs["Tank Charging Characteristics"][
        "TES Hot Max % of Total Tank Volume moved in 1 hr"
    ]
    TES_inputs["Tank Charging Characteristics"]["TES Hot Max Flow"] = (
        math.ceil((hot_volume1 * hot_tankVolumeMoved) / 60 / 5) * 5
    )

    # TES Cold Capacity
    GALtoLbs = TES_inputs["Conversion Rates"]["GAL to Lbs"]
    upperColdTemp = TES_inputs["Initial Conditions"]["TES Cold Tank Upper Tank Temp"]
    lowerColdTemp = TES_inputs["Initial Conditions"]["TES Cold Tank Lower Tank Temp"]
    TES_inputs["Tank Charging Characteristics"]["TES Cold Capacity"] = (
        GALtoLbs * (upperColdTemp - lowerColdTemp) * cold_volume1 / 1000
    )
    # TES Cold Max Flow
    cold_tankVolumeMoved = TES_inputs["Tank Charging Characteristics"][
        "TES Cold Max % of Total Tank Volume moved in 1 hr"
    ]
    TES_inputs["Tank Charging Characteristics"]["TES Cold Max Flow"] = (
        math.ceil((cold_volume1 * cold_tankVolumeMoved) / 60 / 5) * 5
    )
    return CUP_inputs, building_inputs, TES_inputs


# call function to modify the three dicts
CUP_inputs, building_inputs, TES_inputs = calculate_inputs(
    CUP_inputs,
    building_inputs,
    TES_inputs,
    hotWater_schedule3_inputs_df,
    chilledCTOcean_schedule5_inputs_df,
)


###############Static inputs###############

# import Weather data
weather_df = pd.read_excel("Weather data.xlsx")


# import Ocean data
ocean_df = pd.read_excel("Ocean temp.xlsx")


# import heat pump data
heatPump_df = pd.read_excel("CO2 heat pump details.xlsx")

# import Date and Time
dateTime_df = pd.read_excel("Date and Time.xlsx")

buildingModule_inputs = pd.DataFrame()
districtModule_inputs = pd.DataFrame()

districtModule_inputs["Ambient Temperature (°F)"] = weather_df["Dry Bulb Temp (°F)"]

##Loop HW STP (°F)
# Extract columns from input_fields_df
hotWaterMonths = hotWater_schedule3_inputs_df["Schedules Month"].values
hotWaterSetpointCUP = hotWater_schedule3_inputs_df["CUP"].values


# Extract month from weather date time column
dateTime_df["Date and Time"] = pd.to_datetime(dateTime_df["Date and Time"], unit="D")
dateTime = dateTime_df["Date and Time"]
month_to_match = dateTime_df["Date and Time"].dt.month.values
days_to_match = dateTime_df["Date and Time"].dt.day.values

# Find the index where month matches
HW_indices = np.where(month_to_match[:, None] == hotWaterMonths)[1]

# Get the corresponding value from hotWaterSetpoint column
districtModule_inputs["Loop HW STP (°F)"] = hotWaterSetpointCUP[HW_indices]

##Building HHW STP (°F)
# Extract columns from input_fields_df
hotWaterSetpointBldg = hotWater_schedule3_inputs_df["Building"].values

# Get the corresponding value from hotWaterSetpoint column
buildingModule_inputs["Building HHW STP (°F)"] = hotWaterSetpointBldg[HW_indices]


##Loop CHW STP (°F)
# Extract columns from input_fields_df
chilledWaterMonths = chilledCTOcean_schedule5_inputs_df.loc[
    chilledCTOcean_schedule5_inputs_df["Schedules Category"] == "Chilled Water Setpoint",
    "Month",
].values
chilledWaterSetpointBldg = chilledCTOcean_schedule5_inputs_df.loc[
    chilledCTOcean_schedule5_inputs_df["Schedules Category"] == "Chilled Water Setpoint",
    "CUP",
].values

# Find the index where month matches
CH_indices = np.where(month_to_match[:, None] == chilledWaterMonths)[1]

# Get the corresponding value from hotWaterSetpoint column
districtModule_inputs["Loop CHW STP (°F)"] = chilledWaterSetpointBldg[CH_indices]

# Extract columns from input_fields_df
coldWaterMonths = chilledCTOcean_schedule5_inputs_df.loc[
    chilledCTOcean_schedule5_inputs_df["Schedules Category"] == "Chilled Water Setpoint",
    "Month",
].values
coldWaterSetpointCUP = chilledCTOcean_schedule5_inputs_df.loc[
    chilledCTOcean_schedule5_inputs_df["Schedules Category"] == "Chilled Water Setpoint",
    "CUP",
].values

# Find the index where month matches
CHW_indices = np.where(month_to_match[:, None] == coldWaterMonths)[1]

# Get the corresponding value from hotWaterSetpoint column
districtModule_inputs["District CHW STP (°F)"] = coldWaterSetpointCUP[CHW_indices]
