from typing import Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, computed_field, validator


class heatPump(BaseModel):
    districtHWRT: pd.Series
    districtCHWRT: pd.Series
    districtHWSflow: pd.Series
    HW_districtSTP: pd.Series
    HP_leavingHW: pd.Series
    HP_enteringHW: pd.Series
    HP_enteringCHW: pd.Series
    HP_leavingCHW: pd.Series
    HP_maxHeating: pd.Series
    HP_maxCooling: pd.Series
    TES_H_shiftChargeRate: pd.Series
    TES_H_flowOut: pd.Series
    HP_heatingCapacity: float
    HP_coolingCapacity: float
    TES_C_shiftChargeRate: pd.Series = None
    TES_C_flowOut: pd.Series = None
    TES_H_tempOut: pd.Series = None
    TES_C_tempOut: pd.Series = None
    districtCHWSflow: pd.Series
    dryBulb_temp: pd.Series
    wetBulb_temp: pd.Series
    HP_waterSource: float
    HP_airWaterSource: float

    grReturn_D_LWT: pd.Series
    gr_months: pd.Series
    month_to_match: np.ndarray
    ocean_df: pd.DataFrame
    days_to_match: np.ndarray
    ocean_df_WS_temporary: pd.Series
    HP_grSource_capacity: float
    HP_ocean_capacity: float
    HP_CT_capacity: float

    chiller_maxCapacity: float

    grReturn_HtRej_LWT: pd.Series

    CT_CUP_value: pd.Series
    CT_CUP_month: pd.Series
    CHW_districtSTP: pd.Series

    Electric_Chiller_maxLift_input: float

    Electric_Chiller_minLift_input: float
    Electric_Chiller_capacity_minLift_input: float

    # boiler input
    TES_H_flowOut: pd.Series
    boiler_maxCapacity_input: float
    boiler_efficiency_input: float

    # HS-HS input
    grReturn_HtEx_EWT: pd.Series
    grReturn_HtRej_EWT: pd.Series
    HSHS_deltaT_HP: float
    HSHS_deltaT_CH: float

    class MySeries(BaseModel):
        data: dict[str, Union[int, float, str]]  # Dictionary to store Series data

        @validator("data")
        def validate_data(cls, value):
            # Add validation logic here if needed (e.g., check data types, keys)
            return value

    class Config:
        arbitrary_types_allowed = True

    def min_diff(self, data: pd.Series, target: pd.Series) -> int:
        # Convert data_series and target_series to NumPy arrays for numerical operations
        data_values = data.values
        target_values = target.values
        # data_values = self.HP_enteringHW.values
        # target_values = self.districtHWRT.values

        # Reshape self.data to (1, 4) to broadcast across self.target
        data_values_reshaped = data_values.reshape(1, -1)  # Shape (1, 4)

        # Subtract each element of data_values_reshaped from every element of self.target
        diff = abs(target_values[:, np.newaxis] - data_values_reshaped)  # Broadcasting happens here
        # diff now has shape (8760, 4), where each row contains the differences

        # # Find the index of the minimum absolute difference for each element in self.target
        # min_index = np.argmin(np.abs(diff), axis=1)
        # # min_index now has shape (8760,) containing indices of minimum absolute differences
        # min_index = pd.Series(min_index)
        return (diff, np.min(diff, axis=1))

    # the following three functions were giving wierd indices,check code
    @computed_field
    @property
    def CHWST(self) -> pd.Series:
        diff_HW_HWRT, min_diff_HW_HWRT = self.min_diff(self.HP_enteringHW, self.districtHWRT)
        diff_CHW_CHWRT, min_diff_CHW_CHWRT = self.min_diff(self.HP_enteringCHW, self.districtCHWRT)
        # reshaped_HP_leavingHW = self.HP_leavingHW.values.reshape((1, self.HP_leavingHW.size))
        # # Assuming self.HW_districtSTP is a pandas Series
        # rereshaped_HP_leavingHW = np.tile(reshaped_HP_leavingHW, (8760, 1))
        # reshape to convert single row to multiple rows to be able to broadcast
        rereshaped_HP_leavingHW = self.HP_leavingHW.values[np.newaxis, :].repeat(8760, axis=0)
        HW_districtSTP = self.HW_districtSTP.values
        HW_districtSTP = self.HW_districtSTP.values.reshape((-1, 1))
        matching_indices = np.where(
            (diff_HW_HWRT == min_diff_HW_HWRT[:, np.newaxis])
            & (diff_CHW_CHWRT == min_diff_CHW_CHWRT[:, np.newaxis])
            & (rereshaped_HP_leavingHW == HW_districtSTP)
        )[1]
        # Get the corresponding value from AE based on the matching index
        final_value = self.HP_leavingCHW[matching_indices] if matching_indices.size > 0 else None
        return final_value.reset_index(drop=True)

    @computed_field
    @property
    def heatingOutput(self) -> pd.Series:
        # get difference and min difference from the function
        diff_HW_HWRT, min_diff_HW_HWRT = self.min_diff(self.HP_enteringHW, self.districtHWRT)
        diff_CHW_CHWRT, min_diff_CHW_CHWRT = self.min_diff(self.HP_enteringCHW, self.districtCHWRT)
        # reshape to first convert single row with values then to multiple rows to be able to broadcast
        rereshaped_HP_leavingHW = self.HP_leavingHW.values[np.newaxis, :].repeat(8760, axis=0)
        HW_districtSTP = self.HW_districtSTP.values.reshape((-1, 1))
        matching_indices = np.where(
            (diff_HW_HWRT == min_diff_HW_HWRT[:, np.newaxis])
            & (diff_CHW_CHWRT == min_diff_CHW_CHWRT[:, np.newaxis])
            & (rereshaped_HP_leavingHW == HW_districtSTP)
        )[1]
        final_value = self.HP_maxHeating[matching_indices] if matching_indices.size > 0 else None
        return final_value.reset_index(drop=True)

    @computed_field
    @property
    def coolingOutput(self) -> pd.Series:
        diff_HW_HWRT, min_diff_HW_HWRT = self.min_diff(self.HP_enteringHW, self.districtHWRT)
        diff_CHW_CHWRT, min_diff_CHW_CHWRT = self.min_diff(self.HP_enteringCHW, self.districtCHWRT)
        # reshape to convert single row to multiple rows to be able to broadcast
        rereshaped_HP_leavingHW = self.HP_leavingHW.values[np.newaxis, :].repeat(8760, axis=0)
        HW_districtSTP = self.HW_districtSTP.values.reshape((-1, 1))
        matching_indices = np.where(
            (diff_HW_HWRT == min_diff_HW_HWRT[:, np.newaxis])
            & (diff_CHW_CHWRT == min_diff_CHW_CHWRT[:, np.newaxis])
            & (rereshaped_HP_leavingHW == HW_districtSTP)
        )[1]
        final_value = self.HP_maxCooling[matching_indices] if matching_indices.size > 0 else None
        return final_value.reset_index(drop=True)

    @computed_field
    @property
    def heatCoolRatio(self) -> pd.Series:
        # print("ppp",self.coolingOutput)
        return self.heatingOutput / self.coolingOutput

    @computed_field
    @property
    def reqHeatingOutput(self) -> pd.Series:
        value1 = (
            (self.districtHWSflow + self.TES_H_shiftChargeRate - self.TES_H_flowOut)
            * 500
            * (self.HW_districtSTP - self.districtHWRT)
        )
        minimum = pd.Series(np.minimum(value1, self.HP_heatingCapacity))
        # print("value1",value1,"self.HP_heatingCapacity",self.HP_heatingCapacity)
        return minimum

    @computed_field
    @property
    def possRecoveredCHW(self) -> pd.Series:
        value1 = self.reqHeatingOutput / self.heatCoolRatio[0]

        return pd.Series(np.minimum(value1, self.HP_coolingCapacity))

    @computed_field
    @property
    def possRecoveredCHWFLow(self) -> pd.Series:
        return self.possRecoveredCHW / 500 / (self.districtCHWRT - self.CHWST)

    @computed_field
    @property
    def reqHeatingOutput_gpm(self) -> pd.Series:
        return self.reqHeatingOutput / 500 / (self.HW_districtSTP - self.districtHWRT)

    @computed_field
    @property
    def reqCoolingOutput(self) -> pd.Series:
        result_series = (
            (self.districtCHWSflow + self.TES_C_shiftChargeRate - self.TES_C_flowOut)
            * 500
            * (self.districtCHWRT - self.CHWST)
        )
        return result_series

    @computed_field
    @property
    def reqCoolingOutput_gpm(self) -> pd.Series:
        return self.reqCoolingOutput / 500 / (self.districtCHWRT - self.CHWST)

    @computed_field
    @property
    def HP_capacity_C(self) -> pd.Series:
        return pd.Series(np.minimum(self.reqCoolingOutput, self.possRecoveredCHW))

    @computed_field
    @property
    def HP_capacity_H(self) -> pd.Series:
        return self.heatCoolRatio * self.HP_capacity_C

    @computed_field
    @property
    def HP_capacity_H_only(self) -> pd.Series:
        return pd.Series(
            np.minimum(
                self.reqHeatingOutput - self.HP_capacity_H,
                self.HP_heatingCapacity - self.HP_capacity_H,
            )
        )

    ################# ground inputs ##########################
    @computed_field
    @property
    def gr_returnTemp(self) -> pd.Series:
        # Find the index where month matches
        # print("mmm",self.month_to_match[:, None],self.gr_months.values,self.gr_months)
        HW_indices = np.where(self.month_to_match[:, None] == self.gr_months.values)[1]
        # print("llll",HW_indices)
        # Get the corresponding value from hotWaterSetpoint column
        return (self.grReturn_D_LWT[HW_indices] + 0.0001).reset_index(drop=True)

    @computed_field
    @property
    def gr_returnTemp_HtRjt(self) -> pd.Series:
        # Find the index where month matches
        # print("mmm",self.month_to_match[:, None],self.gr_months.values,self.gr_months)
        HW_indices = np.where(self.month_to_match[:, None] == self.gr_months.values)[1]
        # print("llll",HW_indices)
        # Get the corresponding value from hotWaterSetpoint column
        gr_returnTemp_HtRjt = self.grReturn_HtRej_LWT[HW_indices].reset_index(drop=True)

        return gr_returnTemp_HtRjt

    ################# HP ##########################
    @computed_field
    @property
    def oceanWaterTemp(self) -> pd.Series:
        # # # static_input_df = pd.DataFrame()
        # # # Extract day and month from the date
        # day_value = self.days_to_match.astype(str)
        # month_value = self.month_to_match.astype(str)
        # print("day_value",day_value.shape)

        # # Create a combined lookup key as string
        # # lookup_key = [day + month for day, month in zip(day_value, month_value)]
        # lookup_key = np.core.defchararray.add(day_value, month_value)
        # print("lookup_key",lookup_key)
        # print("month_value",month_value.shape,len(lookup_key))
        # # # Create combined lookup column in static input DataFrame
        # # self.ocean_df['CombinedDate'] = self.ocean_df['Day'].astype(str) + self.ocean_df['Month'].astype(str)
        # # print("self.ocean_df",self.ocean_df)
        # # print("self.ocean_df.loc[self.ocean_df['CombinedDate'] == lookup_key]",self.ocean_df.loc[self.ocean_df['CombinedDate'] == lookup_key])
        # # # Find the matching row index in static input DataFrame
        # # match_row = self.ocean_df.loc[self.ocean_df['CombinedDate'] == lookup_key].index[0]

        # # # Get the corresponding value from column W and subtract 0.0001
        # # result_value = self.ocean_df.loc[match_row, self.ocean_df['Surface Temp (°F)']] - 0.0001
        # # return result_value
        #     # Create lookup_key directly from days_to_match and month_to_match numpy arrays
        # # lookup_key = (self.days_to_match.astype(str) + self.month_to_match.astype(str))

        # # Create CombinedDate column in ocean_df to match with lookup_key
        # self.ocean_df['CombinedDate'] = self.ocean_df['Day'].astype(str) + self.ocean_df['Month'].astype(str)
        # print("self.ocean_df['CombinedDate']",self.ocean_df['CombinedDate'])
        # # Merge ocean_df with lookup_key to map ocean temperatures to each hour
        # # merged_df = pd.merge(pd.DataFrame({'CombinedDate': lookup_key}), self.ocean_df,
        # #                     on='CombinedDate', how='left')

        # #         # Create a DataFrame from lookup_key
        # # lookup_df = pd.DataFrame({'CombinedDate': lookup_key})

        # # # Perform a left merge directly on self.ocean_df with lookup_df on 'CombinedDate'
        # # merged_df = self.ocean_df.merge(lookup_df, on='CombinedDate', how='left')

        # #.set_index('CombinedDate')
        # # Create a DataFrame from lookup_key with CombinedDate as the index
        # lookup_df = pd.DataFrame({'CombinedDate': lookup_key}).set_index('CombinedDate')
        # print("fffffflookup_df",lookup_df)
        # # Set CombinedDate as the index in self.ocean_df
        # ocean_df_indexed = self.ocean_df.set_index('CombinedDate')
        # # print("Unique values in lookup_df['CombinedDate']: ", lookup_df['CombinedDate'].nunique())
        # # print("Unique values in self.ocean_df['CombinedDate']: ", self.ocean_df['CombinedDate'].nunique())

        #     # Merge ocean_df with lookup_df based on 'CombinedDate' using merge function
        # # Merge ocean_df with lookup_df based on 'CombinedDate' using merge function
        # # merged_df = pd.merge(lookup_df, self.ocean_df, on='CombinedDate', how='left', suffixes=('', '_right'), validate='1:1')

        # # Perform a left join using .join() on the indexed DataFrames
        # merged_df = ocean_df_indexed.join(lookup_df, how='left')

        # # Reset the index to make CombinedDate a regular column
        # merged_df.reset_index(inplace=True)
        # print("merged_df",merged_df,merged_df['Surface Temp (°F)'].shape)

        # # Adjust the mapped ocean temperatures by subtracting 0.0001
        # mapped_temps = merged_df['Surface Temp (°F)'] - 0.0001

        # # Return the mapped temperatures as MySeries
        # return pd.Series(mapped_temps),pd.Series(merged_df['CombinedDate']),pd.Series(day_value).reset_index(drop=True),pd.Series(month_value).reset_index(drop=True),pd.Series(lookup_key).reset_index(drop=True)
        # # return pd.Series(mapped_temps),pd.Series(merged_df['CombinedDate'])

        #         # Convert days_to_match and month_to_match to string
        # day_value = self.days_to_match.astype(str)
        # month_value = self.month_to_match.astype(str)

        # # Create combined lookup key as string
        # lookup_key = np.core.defchararray.add(day_value, month_value)

        # # Create CombinedDate column in ocean_df to match with lookup_key
        # # self.ocean_df['CombinedDate'] = self.ocean_df['Day'].astype(str) + self.ocean_df['Month'].astype(str)
        # # Set CombinedDate as index in ocean_df
        # # self.ocean_df.set_index('CombinedDate', inplace=True)

        # # Create a Series to hold the mapped temperatures
        # mapped_temps = pd.Series(index=lookup_key, dtype=float)
        # print(self.ocean_df["CombinedDate"])
        # # Iterate over each unique CombinedDate in lookup_key
        # for combined_date in np.unique(lookup_key):
        #     print("combined_date",combined_date)
        #     combined_date = int(combined_date)
        #     # Check if the CombinedDate exists in ocean_df
        #     if combined_date in self.ocean_df["CombinedDate"]:

        #         # Get the Surface Temp (°F) value for the CombinedDate
        #         temp_value = self.ocean_df.loc[self.ocean_df["CombinedDate"]==combined_date, 'Surface Temp (°F)']
        #         print("temp_value",temp_value)
        #         temp_value = float(temp_value.iloc[0])
        #         # Assign the temperature to the mapped_temps Series
        #         mapped_temps[combined_date] = temp_value - 0.0001  # Adjust the temperature

        # # Reset index of mapped_temps to make CombinedDate a regular column
        # mapped_temps = mapped_temps.reset_index()

        # # Rename the columns for clarity
        # mapped_temps.columns = ['MappedTemp',"x"]

        # return pd.Series(mapped_temps['x']),pd.Series(day_value).reset_index(drop=True),pd.Series(month_value).reset_index(drop=True),pd.Series(lookup_key).reset_index(drop=True)
        return self.ocean_df_WS_temporary

    @computed_field
    @property
    def HP_capacity_H_only_WS(self) -> pd.Series:
        # Calculate the first condition (G3 > H3) & (G3 > D3)
        first_condition = (self.dryBulb_temp > self.gr_returnTemp) & (self.gr_returnTemp > self.oceanWaterTemp)

        # Calculate the value when the first condition is True
        max_value = (self.HP_capacity_H_only - self.HP_heatingCapacity * self.HP_airWaterSource).clip(lower=0)
        first_result = pd.Series(
            np.minimum(
                max_value,
                self.HP_heatingCapacity * (self.HP_waterSource + self.HP_airWaterSource),
            )
        )

        # Calculate the value when the first condition is False
        second_result = pd.Series(
            np.minimum(
                self.HP_capacity_H_only,
                self.HP_heatingCapacity * (self.HP_waterSource + self.HP_airWaterSource),
            )
        )

        # Initialize result Series with the same index as self.HP_capacity_H_only
        result = pd.Series(index=self.HP_capacity_H_only.index)

        # Apply the condition using boolean indexing
        result[first_condition] = first_result[first_condition]
        result[~first_condition] = second_result[~first_condition]

        # Return the result Series
        return result

    @computed_field
    @property
    def HP_capacity_H_only_GS(self) -> pd.Series:
        # Calculate the first condition H3 > D3
        first_condition = self.gr_returnTemp > self.oceanWaterTemp

        # Calculate MIN(AM3, GS_Cap)
        min_AM3_GS_Cap = pd.Series(np.minimum(self.HP_capacity_H_only_WS, self.HP_grSource_capacity))

        # Calculate MIN(AM3 - MIN(AM3, SW_Cap), GS_Cap)
        min_AM3_SW_GS_Cap = pd.Series(
            np.minimum(
                self.HP_capacity_H_only_WS - pd.Series(np.minimum(self.HP_capacity_H_only_WS, self.HP_ocean_capacity)),
                self.HP_grSource_capacity,
            )
        )

        # min_AM3_SW_GS_Cap = min_AM3_SW_GS_Cap.where(min_AM3_SW_GS_Cap > 0, 0)  # Ensure non-negative result

        # Apply the condition using boolean indexing
        result = pd.Series(
            index=self.HP_capacity_H_only_WS.index
        )  # Initialize result Series with the same index as AM3
        result[first_condition] = min_AM3_GS_Cap
        result[~first_condition] = min_AM3_SW_GS_Cap

        # Return the result Series
        return result

    # =IF(H3<=D3,MIN(AM3,SW_Cap),MIN(AM3-MIN(AM3,GS_Cap),SW_Cap))
    @computed_field
    @property
    def HP_capacity_H_only_OS(self) -> pd.Series:
        # Calculate the first condition (G3 > H3) & (G3 > D3)
        first_condition = self.gr_returnTemp <= self.oceanWaterTemp

        # Calculate MIN(AM3, GS_Cap)
        min1 = pd.Series(np.minimum(self.HP_capacity_H_only_WS, self.HP_ocean_capacity))

        # Calculate MIN(AM3 - MIN(AM3, SW_Cap), GS_Cap)
        min2 = pd.Series(
            np.minimum(
                self.HP_capacity_H_only_WS
                - pd.Series(np.minimum(self.HP_capacity_H_only_WS, self.HP_grSource_capacity)),
                self.HP_ocean_capacity,
            )
        )

        # min_AM3_SW_GS_Cap = min_AM3_SW_GS_Cap.where(min_AM3_SW_GS_Cap > 0, 0)  # Ensure non-negative result

        # Apply the condition using boolean indexing
        result = pd.Series(
            index=self.HP_capacity_H_only_WS.index
        )  # Initialize result Series with the same index as AM3
        result[first_condition] = min1
        result[~first_condition] = min2

        # Return the result Series
        return result

    # =IF(AND(G3>H3,G3>D3),MIN(AK3,AS_WS_pct*HP_HT_Cap),MIN(AK3-AN3-AO3,HP_HT_Cap*AS_WS_pct))
    @computed_field
    @property
    def HP_capacity_H_only_AS(self) -> pd.Series:
        # Calculate the first condition H3 > D3
        first_condition = (self.dryBulb_temp > self.gr_returnTemp) & (self.gr_returnTemp > self.oceanWaterTemp)

        # Calculate MIN(AM3, GS_Cap)
        minimum1 = pd.Series(
            np.minimum(
                self.HP_capacity_H_only,
                self.HP_heatingCapacity * self.HP_airWaterSource,
            )
        )

        # pd.concat([self.HP_capacity_H_only_WS, self.HP_grSource_capacity], axis=1).min(axis=1)

        # Calculate MIN(AM3 - MIN(AM3, SW_Cap), GS_Cap)
        minimum2 = pd.Series(
            np.minimum(
                self.HP_capacity_H_only - self.HP_capacity_H_only_GS - self.HP_capacity_H_only_OS,
                self.HP_heatingCapacity * self.HP_airWaterSource,
            )
        )

        # min_AM3_SW_GS_Cap = min_AM3_SW_GS_Cap.where(min_AM3_SW_GS_Cap > 0, 0)  # Ensure non-negative result

        # Apply the condition using boolean indexing
        result1 = pd.Series(
            index=self.HP_capacity_H_only_WS.index, dtype=float
        )  # Initialize result Series with the same index as AM3
        result1[first_condition] = minimum1
        result1[~first_condition] = minimum2

        # Return the result Series
        return result1

    ########## cooling tower ############

    @computed_field
    @property
    def CTapproach(self) -> pd.Series:
        # print("self.CT_CUP_month.values",self.CT_CUP_month.values)
        HW_indices = np.where(self.month_to_match[:, None] == self.CT_CUP_month.values)[1]
        # print("HW_indices",HW_indices)
        self.CT_CUP_value = self.CT_CUP_value.reset_index(drop=True)
        # Get the corresponding value from hotWaterSetpoint column
        return self.CT_CUP_value[HW_indices].reset_index(drop=True)

    @computed_field
    @property
    def cooler_CWRT(self) -> pd.Series:
        # Calculate the cooler_CWRT Series
        cooler_cwrt_series = self.wetBulb_temp + self.CTapproach

        # Assign a name to the Series
        cooler_cwrt_series.name = "cooler_CWRT"

        return cooler_cwrt_series

    #######chiller#################
    @computed_field
    @property
    def chiller_output(self) -> pd.Series:
        return pd.Series(np.minimum(self.reqCoolingOutput - self.HP_capacity_C, self.chiller_maxCapacity))

    # read this later
    @computed_field
    @property
    def chiller_gr_hRjt(self) -> pd.Series:
        # Apply the logic using pandas operations
        condition1 = (self.gr_returnTemp_HtRjt < self.oceanWaterTemp) & (self.gr_returnTemp_HtRjt < self.cooler_CWRT)
        condition2 = (self.oceanWaterTemp < self.gr_returnTemp_HtRjt) & (self.gr_returnTemp_HtRjt < self.cooler_CWRT)
        condition3 = (self.cooler_CWRT < self.gr_returnTemp_HtRjt) & (self.gr_returnTemp_HtRjt < self.oceanWaterTemp)

        result = pd.Series(np.nan, index=self.gr_returnTemp_HtRjt.index)  # Initialize result Series with NaN
        L3 = self.chiller_output
        GS_Cap = self.HP_grSource_capacity
        SW_Cap = self.HP_ocean_capacity
        CT_Cap = self.HP_CT_capacity
        # Apply logic using broadcasting and scalar values
        result[condition1] = np.minimum(L3[condition1], GS_Cap)
        result[condition2] = np.minimum(GS_Cap, L3[condition2] - np.minimum(L3[condition2], SW_Cap))
        result[condition3] = np.minimum(GS_Cap, L3[condition3] - np.minimum(L3[condition3], CT_Cap))

        # Compute values for other conditions (using scalar values)
        minimum = np.minimum(
            GS_Cap,
            L3[~(condition1 | condition2 | condition3)]
            - np.minimum(L3[~(condition1 | condition2 | condition3)], CT_Cap)
            - np.minimum(L3[~(condition1 | condition2 | condition3)], SW_Cap),
        )
        result[~(condition1 | condition2 | condition3)] = np.maximum(0, minimum)

        return result

    @computed_field
    @property
    def chiller_ocean_hRjt(self) -> pd.Series:
        # Initialize result Series with NaN

        E3 = self.gr_returnTemp_HtRjt
        F3 = self.oceanWaterTemp
        D3 = self.cooler_CWRT
        L3 = self.chiller_output
        GS_Cap = self.HP_grSource_capacity
        SW_Cap = self.HP_ocean_capacity
        CT_Cap = self.HP_CT_capacity

        result = pd.Series(np.nan, index=E3.index)
        # Condition 1: F3 <= E3 and F3 <= D3
        condition1 = (F3 <= E3) & (F3 <= D3)
        result[condition1] = np.minimum(L3[condition1], SW_Cap)

        # Condition 2: E3 < F3 and F3 <= D3
        condition2 = (E3 < F3) & (F3 <= D3)
        result[condition2] = np.minimum(SW_Cap, L3[condition2] - np.minimum(L3[condition2], GS_Cap))

        # Condition 3: D3 < F3 and F3 <= E3
        condition3 = (D3 < F3) & (F3 <= E3)
        result[condition3] = np.minimum(SW_Cap, L3[condition3] - np.minimum(L3[condition3], CT_Cap))

        # Other conditions
        other_conditions = ~(condition1 | condition2 | condition3)
        minimum_value = np.minimum(
            SW_Cap,
            L3[other_conditions] - np.minimum(L3[other_conditions], CT_Cap) - np.minimum(L3[other_conditions], GS_Cap),
        )
        result[other_conditions] = np.maximum(0, minimum_value)

        return result

    @computed_field
    @property
    def chiller_CT_hRjt(self) -> pd.Series:
        E3 = self.gr_returnTemp_HtRjt
        F3 = self.oceanWaterTemp
        D3 = self.cooler_CWRT
        L3 = self.chiller_output
        GS_Cap = self.HP_grSource_capacity
        SW_Cap = self.HP_ocean_capacity
        CT_Cap = self.HP_CT_capacity
        # Initialize result Series with NaN
        result = pd.Series(np.nan, index=D3.index)

        # Condition 1: D3 < F3 and D3 < E3
        condition1 = (D3 < F3) & (D3 < E3)
        result[condition1] = np.minimum(L3[condition1], CT_Cap)

        # Condition 2: F3 < D3 and D3 < E3
        condition2 = (F3 < D3) & (D3 < E3)
        result[condition2] = np.minimum(CT_Cap, L3[condition2] - np.minimum(L3[condition2], SW_Cap))

        # Condition 3: E3 < D3 and D3 < F3
        condition3 = (E3 < D3) & (D3 < F3)
        result[condition3] = np.minimum(CT_Cap, L3[condition3] - np.minimum(L3[condition3], GS_Cap))

        # Other conditions
        other_conditions = ~(condition1 | condition2 | condition3)
        minimum_value = np.minimum(
            CT_Cap,
            L3[other_conditions] - np.minimum(L3[other_conditions], GS_Cap) - np.minimum(L3[other_conditions], SW_Cap),
        )
        result[other_conditions] = np.maximum(0, minimum_value)

        return result

    @computed_field
    @property
    def chiller_CHWSflow(self) -> pd.Series:
        return self.chiller_output / 500 / (self.districtCHWRT - self.CHW_districtSTP)

    @computed_field
    @property
    def chiller_lift(self) -> pd.Series:
        # Calculate the numerator term
        numerator_term = (self.Electric_Chiller_maxLift_input - self.Electric_Chiller_minLift_input) / (
            self.chiller_maxCapacity - self.Electric_Chiller_capacity_minLift_input
        )

        # Initialize an array to store the results
        result = np.zeros_like(self.chiller_output)

        # Apply the formula vectorized
        mask = self.chiller_output >= 1  # Create a mask where L3 >= 1
        result[mask] = np.maximum(
            self.Electric_Chiller_maxLift_input,
            numerator_term * self.chiller_output[mask]
            + (self.chiller_maxCapacity - numerator_term * self.chiller_maxCapacity),
        )

        # Add the result as a new column to the DataFrame
        result_series = pd.Series(result)

        return result_series

    @computed_field
    @property
    def chiller_CWS_temp(self) -> pd.Series:
        # Extract underlying numpy arrays from DataFrame columns
        chiller_lift = self.chiller_lift.values
        CHW_districtSTP = self.CHW_districtSTP.values

        # Calculate chiller_CWS_temp using numpy vectorized operations
        chiller_CWS_temp = np.where(chiller_lift == 0, 0, chiller_lift + CHW_districtSTP)

        # Assign the result back to the DataFrame
        return pd.Series(chiller_CWS_temp)

    ############### HP #################
    @computed_field
    @property
    def HP_capacity_C_only(self) -> pd.Series:
        # =MIN(AE3-AJ3-Chillers!L3,'Input Fields'!$B$11-AJ3)
        return pd.Series(
            np.minimum(
                self.reqCoolingOutput - self.HP_capacity_C - self.chiller_output,
                self.HP_coolingCapacity - self.HP_capacity_C,
            )
        )

    # Function to find the index corresponding to the second smallest value across multiple Series
    def find_x_min_index_across_series(self, position) -> pd.Series:
        series_list = [
            self.oceanWaterTemp,
            self.gr_returnTemp_HtRjt,
            self.cooler_CWRT,
            self.dryBulb_temp,
        ]

        # Concatenate the Series into a DataFrame
        df = pd.concat(series_list, axis=1)

        # Find the indices of the sorted values (ascending order)
        sorted_indices = np.argsort(df.values, axis=1)

        # Get the index of the second smallest value (sorted_indices[:, 1])
        x_min_index = df.columns[sorted_indices[:, position]]

        return x_min_index

    @computed_field
    @property
    def HS_Priority1(self) -> pd.Series:
        self.gr_returnTemp_HtRjt.rename("gr_returnTemp_HtRjt", inplace=True)
        custom_names = {
            "Ht Rej - LWT*": "Ground Source",
            "cooler_CWRT": "Tower Source",
            "Ocean Water Temp (°F) For Water-Source": "Ocean Source",
            "Dry Bulb Temp (°F)": "Air Source",
        }
        # Call the function with the list of Series and map names to get custom names
        min_index_across_series = self.find_x_min_index_across_series(0).map(custom_names)
        return min_index_across_series

    @computed_field
    @property
    def HS_Priority2(self) -> pd.Series:
        custom_names = {
            "Ht Rej - LWT*": "Ground Source",
            "cooler_CWRT": "Tower Source",
            "Ocean Water Temp (°F) For Water-Source": "Ocean Source",
            "Dry Bulb Temp (°F)": "Air Source",
        }
        # Call the function with the list of Series and map names to get custom names
        min_index_across_series = self.find_x_min_index_across_series(1).map(custom_names)
        return min_index_across_series

    @computed_field
    @property
    def HS_Priority3(self) -> pd.Series:
        custom_names = {
            "Ht Rej - LWT*": "Ground Source",
            "cooler_CWRT": "Tower Source",
            "Ocean Water Temp (°F) For Water-Source": "Ocean Source",
            "Dry Bulb Temp (°F)": "Air Source",
        }
        # Call the function with the list of Series and map names to get custom names
        min_index_across_series = self.find_x_min_index_across_series(2).map(custom_names)
        return min_index_across_series

    @computed_field
    @property
    def HS_Priority4(self) -> pd.Series:
        custom_names = {
            "Ht Rej - LWT*": "Ground Source",
            "cooler_CWRT": "Tower Source",
            "Ocean Water Temp (°F) For Water-Source": "Ocean Source",
            "Dry Bulb Temp (°F)": "Air Source",
        }
        # Call the function with the list of Series and map names to get custom names
        min_index_across_series = self.find_x_min_index_across_series(3).map(custom_names)
        return min_index_across_series

    @computed_field
    @property
    def GS_max(self) -> pd.Series:
        # Apply element-wise operations on Series
        min_value = pd.Series(
            np.minimum(
                self.HP_coolingCapacity,
                self.HP_grSource_capacity - self.chiller_gr_hRjt,
            )
        )
        max_value = np.maximum(0, min_value)
        return max_value

    @computed_field
    @property
    def OS_max(self) -> pd.Series:
        # =MAX(0,MIN(HP_CL_Cap,SW_Cap-Chillers!Q3))
        # Apply element-wise operations on Series
        min_value = pd.Series(
            np.minimum(
                self.HP_coolingCapacity,
                self.HP_ocean_capacity - self.chiller_ocean_hRjt,
            )
        )
        max_value = np.maximum(0, min_value)
        return max_value

    @computed_field
    @property
    def CT_max(self) -> pd.Series:
        # =MAX(0,MIN(HP_CL_Cap,SW_Cap-Chillers!Q3))
        # Apply element-wise operations on Series
        min_value = pd.Series(np.minimum(self.HP_coolingCapacity, self.HP_CT_capacity - self.chiller_CT_hRjt))
        max_value = np.maximum(0, min_value)
        return max_value

    def calculate_AS_max(self, row, df) -> float:
        # Check if AQ3 is "Air Source"
        if row["p1"] == "Air Source":
            return self.HP_coolingCapacity * self.HP_airWaterSource

        # Calculate initial value
        value = self.HP_coolingCapacity * self.HP_airWaterSource

        # Calculate subtracted value based on conditions
        if row["p2"] == "Air Source":
            subtract_value = df.loc[row.name, row["p1"]]
        elif row["p3"] == "Air Source":
            subtract_value = df.loc[row.name, row["p1"]] + df.loc[row.name, row["p2"]]
        elif row["p4"] == "Air Source":
            subtract_value = df.loc[row.name, row["p1"]] + df.loc[row.name, row["p2"]] + df.loc[row.name, row["p3"]]
        else:
            subtract_value = 0

        # Apply MAX(0, ...)
        result = max(0, value - subtract_value)

        return result

    @computed_field
    @property
    def AS_max(self) -> pd.Series:
        df = pd.DataFrame(
            {
                "Ground Source": self.GS_max,
                "Tower Source": self.CT_max,
                "Ocean Source": self.OS_max,
                "p1": self.HS_Priority1,
                "p2": self.HS_Priority2,
                "p3": self.HS_Priority3,
                "p4": self.HS_Priority4,
            }
        )
        # Apply custom_formula to each row using apply along rows axis (axis=1)
        df["Result"] = df.apply(lambda row: self.calculate_AS_max(row, df), axis=1)
        return df["Result"]

    # function to calulate source wise capacity- common fn for all four
    def calculate_HP_capacity_C_only_source(self, row, df, source) -> float:
        if row["p1"] == source:
            return min(row["Air Source"], row["HP_coolingOnly"])

        else:
            if row["p2"] == source:
                value_ap = row["HP_coolingOnly"]
                index_aq = df.columns.get_loc(row["p1"])
                value_aq = df.loc[row.name, df.columns[index_aq]]
                # print("index_aq",index_aq,row.name)
                return min(row[source], max(0, value_ap - value_aq))
            if row["p3"] == source:
                value_ap = row["HP_coolingOnly"]
                index_aq = df.columns.get_loc(row["p1"])
                value_aq = df.loc[row.name, df.columns[index_aq]]
                index_ar = df.columns.get_loc(row["p2"])
                value_ar = df.loc[row.name, df.columns[index_ar]]
                return min(row[source], max(0, value_ap - value_aq - value_ar))
            if row["p4"] == source:
                value_ap = row["HP_coolingOnly"]
                index_aq = df.columns.get_loc(row["p1"])
                value_aq = df.loc[row.name, df.columns[index_aq]]
                index_ar = df.columns.get_loc(row["p2"])
                value_ar = df.loc[row.name, df.columns[index_ar]]
                index_as = df.columns.get_loc(row["p3"])
                value_as = df.loc[row.name, df.columns[index_as]]
                return min(row[source], max(0, value_ap - value_aq - value_ar - value_as))

    @computed_field
    @property
    def HP_capacity_C_only_AS(self) -> pd.Series:
        df = pd.DataFrame(
            {
                "Ground Source": self.GS_max,
                "Tower Source": self.CT_max,
                "Ocean Source": self.OS_max,
                "Air Source": self.AS_max,
                "p1": self.HS_Priority1,
                "p2": self.HS_Priority2,
                "p3": self.HS_Priority3,
                "p4": self.HS_Priority4,
                "HP_coolingOnly": self.HP_capacity_C_only,
            }
        )

        # print("value",self.HP_coolingCapacity,self.HP_airWaterSource,self.HP_coolingCapacity * self.HP_airWaterSource)
        df["Result"] = df.apply(
            lambda row: self.calculate_HP_capacity_C_only_source(row, df, "Air Source"),
            axis=1,
        )
        return df["Result"]

    @computed_field
    @property
    def HP_capacity_C_only_GS(self) -> pd.Series:
        df = pd.DataFrame(
            {
                "Ground Source": self.GS_max,
                "Tower Source": self.CT_max,
                "Ocean Source": self.OS_max,
                "Air Source": self.AS_max,
                "p1": self.HS_Priority1,
                "p2": self.HS_Priority2,
                "p3": self.HS_Priority3,
                "p4": self.HS_Priority4,
                "HP_coolingOnly": self.HP_capacity_C_only,
            }
        )

        df["Result"] = df.apply(
            lambda row: self.calculate_HP_capacity_C_only_source(row, df, "Ground Source"),
            axis=1,
        )
        return df["Result"]

    @computed_field
    @property
    def HP_capacity_C_only_OS(self) -> pd.Series:
        df = pd.DataFrame(
            {
                "Ground Source": self.GS_max,
                "Tower Source": self.CT_max,
                "Ocean Source": self.OS_max,
                "Air Source": self.AS_max,
                "p1": self.HS_Priority1,
                "p2": self.HS_Priority2,
                "p3": self.HS_Priority3,
                "p4": self.HS_Priority4,
                "HP_coolingOnly": self.HP_capacity_C_only,
            }
        )

        df["Result"] = df.apply(
            lambda row: self.calculate_HP_capacity_C_only_source(row, df, "Ocean Source"),
            axis=1,
        )
        return df["Result"]

    @computed_field
    @property
    def HP_capacity_C_only_TS(self) -> pd.Series:
        df = pd.DataFrame(
            {
                "Ground Source": self.GS_max,
                "Tower Source": self.CT_max,
                "Ocean Source": self.OS_max,
                "Air Source": self.AS_max,
                "p1": self.HS_Priority1,
                "p2": self.HS_Priority2,
                "p3": self.HS_Priority3,
                "p4": self.HS_Priority4,
                "HP_coolingOnly": self.HP_capacity_C_only,
            }
        )

        df["Result"] = df.apply(
            lambda row: self.calculate_HP_capacity_C_only_source(row, df, "Tower Source"),
            axis=1,
        )
        return df["Result"]

    @computed_field
    @property
    def HP_HW_gpm(self) -> pd.Series:
        return (self.HP_capacity_H + self.HP_capacity_H_only) / 500 / (self.HW_districtSTP - self.districtHWRT)

    @computed_field
    @property
    def to_HW_district(self) -> pd.Series:
        return self.HP_HW_gpm - self.TES_H_shiftChargeRate

    @computed_field
    @property
    def HP_CHW_gpm(self) -> pd.Series:
        return (self.HP_capacity_C + self.HP_capacity_C_only) / 500 / (self.districtCHWRT - self.CHWST)

    @computed_field
    @property
    def to_CHW_district(self) -> pd.Series:
        return self.HP_CHW_gpm - self.TES_C_shiftChargeRate

    ##########cooling tower###########

    @computed_field
    @property
    def CT_CWSflow(self) -> pd.Series:
        return (self.chiller_CT_hRjt + self.HP_capacity_C_only_TS) / 500 / (self.cooler_CWRT - self.wetBulb_temp)

    ############### boiler ####################

    @computed_field
    @property
    def boiler_output(self) -> pd.Series:
        result = np.minimum(
            self.boiler_maxCapacity_input,
            (self.districtHWSflow - self.to_HW_district - self.TES_H_flowOut)
            * 500
            * (self.HW_districtSTP - self.districtHWRT),
        )
        return pd.Series(result)

    @computed_field
    @property
    def boiler_HWSflow(self) -> pd.Series:
        return self.boiler_output / 500 / (self.HW_districtSTP - self.districtHWRT)

    @computed_field
    @property
    def boiler_energy(self) -> pd.Series:
        efficiency = pd.Series([self.boiler_efficiency_input] * 8760)
        return (self.boiler_output / efficiency) / 3412

    ######################## HS-HS ####################

    @computed_field
    @property
    def gr_returnTemp_HtExEWT(self) -> pd.Series:
        # Find the index where month matches
        HW_indices = np.where(self.month_to_match[:, None] == self.gr_months.values)[1]
        # print("HW_indices",HW_indices)
        # Get the corresponding value from hotWaterSetpoint column
        result_series = self.grReturn_HtEx_EWT[HW_indices].reset_index(drop=True)

        return result_series

    @computed_field
    @property
    def gr_HtEx_HP_Heating_gpm(self) -> pd.Series:
        return self.HP_capacity_H_only_GS / 500 / (self.gr_returnTemp - self.gr_returnTemp_HtExEWT)

    @computed_field
    @property
    def gr_HtEx_HP_Heating_btuh(self) -> pd.Series:
        return self.gr_HtEx_HP_Heating_gpm * 500 * (self.gr_returnTemp - self.gr_returnTemp_HtExEWT)

    @computed_field
    @property
    def oc_temp_HP_HeatEx(self) -> pd.Series:
        return self.oceanWaterTemp - self.HSHS_deltaT_HP

    @computed_field
    @property
    def oc_H_HP_HeatEx_gpm(self) -> pd.Series:
        return self.HP_capacity_H_only_OS / 500 / (self.oceanWaterTemp - self.oc_temp_HP_HeatEx)

    @computed_field
    @property
    def oc_H_HP_HeatEx_btuh(self) -> pd.Series:
        return self.oc_H_HP_HeatEx_gpm * 500 * (self.oceanWaterTemp - self.oc_temp_HP_HeatEx)

    @computed_field
    @property
    def gr_temp_ENT_HeatRjt(self) -> pd.Series:
        # Find the index where month matches
        HW_indices = np.where(self.month_to_match[:, None] == self.gr_months.values)[1]

        # Get the corresponding value from hotWaterSetpoint column
        result_series = self.grReturn_HtRej_EWT[HW_indices].reset_index(drop=True)

        return result_series

    @computed_field
    @property
    def gr_HtRjt_HP_Cooling_gpm(self) -> pd.Series:
        return self.HP_capacity_C_only_GS / 500 / (self.gr_temp_ENT_HeatRjt - self.gr_returnTemp)

    @computed_field
    @property
    def gr_HtRjt_HP_Cooling_btuh(self) -> pd.Series:
        return self.gr_HtRjt_HP_Cooling_gpm * 500 * (self.gr_temp_ENT_HeatRjt - self.gr_returnTemp)

    @computed_field
    @property
    def oc_temp_ENT_HeatRjt(self) -> pd.Series:
        return self.oceanWaterTemp + self.HSHS_deltaT_HP

    @computed_field
    @property
    def oc_HtRjt_HP_Cooling_gpm(self) -> pd.Series:
        return self.HP_capacity_C_only_OS / 500 / (self.oc_temp_ENT_HeatRjt - self.oceanWaterTemp)

    @computed_field
    @property
    def oc_HtRjt_HP_Cooling_btuh(self) -> pd.Series:
        return self.oc_HtRjt_HP_Cooling_gpm * 500 * (self.oc_temp_ENT_HeatRjt - self.oceanWaterTemp)

    @computed_field
    @property
    def ct_temp_HeatRjt(self) -> pd.Series:
        return self.cooler_CWRT + self.HSHS_deltaT_HP

    @computed_field
    @property
    def ct_HtRjt_HP_CWR_gpm(self) -> pd.Series:
        return self.HP_capacity_C_only_TS / 500 / (self.ct_temp_HeatRjt - self.cooler_CWRT)

    @computed_field
    @property
    def ct_HtRjt_HP_CWR_btuh(self) -> pd.Series:
        return self.ct_HtRjt_HP_CWR_gpm * 500 * (self.ct_temp_HeatRjt - self.cooler_CWRT)

    @computed_field
    @property
    def gr_HtRjt_chiller_gpm(self) -> pd.Series:
        return self.chiller_gr_hRjt / 500 / (self.gr_temp_ENT_HeatRjt - self.gr_returnTemp)

    @computed_field
    @property
    def gr_HtRjt_chiller_btuh(self) -> pd.Series:
        return self.gr_HtRjt_chiller_gpm * 500 * (self.gr_temp_ENT_HeatRjt - self.gr_returnTemp)

    @computed_field
    @property
    def oc_ENT_temp_HeatRjt(self) -> pd.Series:
        return self.oceanWaterTemp + self.HSHS_deltaT_CH

    @computed_field
    @property
    def oc_HtRjt_chiller_gpm(self) -> pd.Series:
        return self.chiller_ocean_hRjt / 500 / (self.oc_ENT_temp_HeatRjt - self.oceanWaterTemp)

    @computed_field
    @property
    def oc_HtRjt_chiller_btuh(self) -> pd.Series:
        return self.oc_HtRjt_chiller_gpm * 500 * (self.oc_ENT_temp_HeatRjt - self.oceanWaterTemp)

    @computed_field
    @property
    def ct_chiller_HeatRjt(self) -> pd.Series:
        return self.cooler_CWRT + self.HSHS_deltaT_CH

    @computed_field
    @property
    def ct_chiller_HeatRjt_gpm(self) -> pd.Series:
        return self.chiller_CT_hRjt / 500 / (self.ct_chiller_HeatRjt - self.cooler_CWRT)

    @computed_field
    @property
    def ct_chiller_HeatRjt_btuh(self) -> pd.Series:
        return self.ct_chiller_HeatRjt_gpm * 500 * (self.ct_chiller_HeatRjt - self.cooler_CWRT)

    @computed_field
    @property
    def total_WS_HeatExt_shortfall(self) -> pd.Series:
        print(
            "hiiiii",
            self.HP_capacity_H_only,
            self.HP_capacity_H_only_AS,
            self.gr_HtEx_HP_Heating_btuh,
            self.oc_H_HP_HeatEx_btuh,
        )
        return (
            self.HP_capacity_H_only
            - self.HP_capacity_H_only_AS
            - self.gr_HtEx_HP_Heating_btuh
            - self.oc_H_HP_HeatEx_btuh
        )

    @computed_field
    @property
    def total_WS_HeatRjt_shortfall(self) -> pd.Series:
        return (
            self.HP_capacity_C_only
            + self.chiller_output
            - self.HP_capacity_C_only_AS
            - self.gr_HtRjt_HP_Cooling_btuh
            - self.oc_HtRjt_HP_Cooling_btuh
            - self.ct_HtRjt_HP_CWR_btuh
            - self.gr_HtRjt_chiller_btuh
            - self.oc_HtRjt_chiller_btuh
            - self.ct_chiller_HeatRjt_btuh
        )

    @computed_field
    @property
    def check_1(self) -> pd.Series:
        return self.HP_capacity_H_only_GS * self.HP_capacity_C_only_GS

    @computed_field
    @property
    def check_2(self) -> pd.Series:
        return self.HP_capacity_H_only_GS * self.chiller_gr_hRjt

    ######################## final results compute to df ###############
    def compute(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "HP CHWST (°F)": self.CHWST,
                "Max Unitary Heating Output (Btu/h)": self.heatingOutput,
                "Max Unitary Cooling Output (Btu/h)": self.coolingOutput,
                "Heat:Cool": self.heatCoolRatio,
                "Required Heating Output (Btu/h)": self.reqHeatingOutput,
                "HWSFLow": self.districtHWSflow,
                "self.HW_districtSTP": self.HW_districtSTP,
                "self.districtHWRT": self.districtHWRT,
                "Possible Recovered CHW (Btu/h)": self.possRecoveredCHW,
                "Possible Recovered CHW (gpm)": self.possRecoveredCHWFLow,
            }
        )

        return df

    def compute2(self) -> pd.DataFrame:
        # x,a,b,c= self.oceanWaterTemp
        df2 = pd.DataFrame(
            {
                "Required Heating Output (gpm)": self.reqHeatingOutput_gpm,
                "Required Cooling Output (Btu/h)": self.reqCoolingOutput,
                "Required Cooling Output (gpm)": self.reqCoolingOutput_gpm,
                "Heat Pumps Heating+Cooling Capacity_(Cooling, Btu/h)": self.HP_capacity_C,
                "Heat Pumps Heating+Cooling Capacity_(Heating, Btu/h)": self.HP_capacity_H,
                "Total Heat Pump Heating Only Capacity": self.HP_capacity_H_only,
                "Ground Water Return Temp (°F)": self.gr_returnTemp,
                "Ambient Dry-bulb Temp (°F)": self.dryBulb_temp,
                "Ocean Water Temp (°F)": self.oceanWaterTemp,
                "Heat Pumps Heating Only Capacity_Water-Source (Btu/h)": self.HP_capacity_H_only_WS,
                "Heat Pumps Heating Only Capacity_Ground Source (Btu/h)": self.HP_capacity_H_only_GS,
                "Heat Pumps Heating Only Capacity_Ocean-Source (Btu/h)": self.HP_capacity_H_only_OS,
                "Heat Pumps Heating Only Capacity_Air-Source (Btu/h)": self.HP_capacity_H_only_AS,
                "Total Heat Pump Cooling Only Capacity": self.HP_capacity_C_only,
                "cooler_CWRT": self.cooler_CWRT,
                "Ground Water Return Temp (°F) For Water-Source Heat Rejection": self.gr_returnTemp_HtRjt,
                "Priority 1_Heat Sink": self.HS_Priority1,
                "Priority 2_Heat Sink": self.HS_Priority2,
                "Priority 3_Heat Sink": self.HS_Priority3,
                "Priority 4_Heat Sink": self.HS_Priority4,
                "Ground Source Max (Btu/h)": self.GS_max,
                "Ocean Source Max (Btu/h)": self.OS_max,
                "Tower Source Max (Btu/h)": self.CT_max,
                "Air Source Max (Btu/h)": self.AS_max,
                "Heat Pumps Cooling Only Capacity_Air-Source (Btu/h)": self.HP_capacity_C_only_AS,
                "Heat Pumps Cooling Only Capacity_Ground-Source (Btu/h)": self.HP_capacity_C_only_GS,
                "Heat Pumps Cooling Only Capacity_Ocean-Source (Btu/h)": self.HP_capacity_C_only_OS,
                "Heat Pumps Cooling Only Capacity_Tower-Source (Btu/h)": self.HP_capacity_C_only_TS,
                "Heat Pump Hot Water (gpm)": self.HP_HW_gpm,
                "To HW District (gpm)": self.to_HW_district,
                "Heat Pump Chilled Water (gpm)": self.HP_CHW_gpm,
                "To CHW District (gpm)": self.to_CHW_district,
            }
        )

        return df2

    def compute_chiller(self) -> pd.DataFrame:
        chiller_df = pd.DataFrame(
            {
                "Chiller Output (Btu/h)": self.chiller_output,
                "Chiller CHWS Flow (gpm)": self.chiller_CHWSflow,
                "Chiller_Heat Rejection-Ground Source (Btu/h)": self.chiller_gr_hRjt,
                "Chiller_Heat Rejection-Ocean Source (Btu/h)": self.chiller_ocean_hRjt,
                "Chiller_Heat Rejection-Tower Source (Btu/h)": self.chiller_CT_hRjt,
                "Chiller Lift (°F)": self.chiller_lift,
                "Chiller CWS Temp (°F)": self.chiller_CWS_temp,
            }
        )

        return chiller_df

    def compute_cooler(self) -> pd.DataFrame:
        cooler_df = pd.DataFrame(
            {
                "Cooling Tower Approach (°F)": self.CTapproach,
                "CWRT (°F)": self.cooler_CWRT,
                "CWS Flow (gpm)": self.CT_CWSflow,
            }
        )

        return cooler_df

    def compute_boiler(self) -> pd.DataFrame:
        boiler_df = pd.DataFrame(
            {
                "Boiler Output (Btu/h)": self.boiler_output,
                "Boiler HWS Flow (gpm)": self.boiler_HWSflow,
                "Energy Consumed (kWh)": self.boiler_energy,
            }
        )
        return boiler_df

    def compute_HS_HS(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "Ground Water Entering Temp (°F)_Heat Extraction": self.gr_returnTemp_HtExEWT,
                "Ground Source Heat Extraction_HP Heating (gpm)": self.gr_HtEx_HP_Heating_gpm,
                "Ground Source Heat Extraction_HP Heating (Btu/h)": self.gr_HtEx_HP_Heating_btuh,
                "Ocean Water Entering Temp (°F) HP Heat Extraction": self.oc_temp_HP_HeatEx,
                "Ocean Source Heat Extraction gpm": self.oc_H_HP_HeatEx_gpm,
                "Ocean Source Heat Extraction btu/h": self.oc_H_HP_HeatEx_btuh,
                "Ground Water Entering Temp (°F)_Heat Rejection": self.gr_temp_ENT_HeatRjt,
                "Ground Source Heat Rejection HP Cooling (gpm)": self.gr_HtRjt_HP_Cooling_gpm,
                "Ground Source Heat Rejection HP Cooling (btuh)": self.gr_HtRjt_HP_Cooling_btuh,
                "Ocean Water Entering Temp (°F)": self.oc_temp_ENT_HeatRjt,
                "Ocean Source Heat Rejection_HP Cooling (gpm)": self.oc_HtRjt_HP_Cooling_gpm,
                "Ocean Source Heat Rejection_HP Cooling (btu/h)": self.oc_HtRjt_HP_Cooling_btuh,
                "Tower CWS Temp (°F) HP Heat Rejection": self.ct_temp_HeatRjt,
                "Tower CWR Flow (gpm) HP Heat Rejection": self.ct_HtRjt_HP_CWR_gpm,
                "Tower Source  HP Heat Rejection (Btu/h)": self.ct_HtRjt_HP_CWR_btuh,
                "Ground Source Heat Rejection Chiller (gpm)": self.gr_HtRjt_chiller_gpm,
                "Ground Source Heat Rejection Chiller (Btu/h)": self.gr_HtRjt_chiller_btuh,
                "Ocean Water Entering Temp (°F) Chiller Heat Rejection": self.oc_ENT_temp_HeatRjt,
                "Ocean Water Heat Rejection Chillers (gpm)": self.oc_HtRjt_chiller_gpm,
                "Ocean Water Heat Rejection Chiller (Btu/h)": self.oc_HtRjt_chiller_btuh,
                "Tower CWS Temp (°F) Chiller Heat Rejection": self.ct_chiller_HeatRjt,
                "Tower CWR Flow (gpm) Chiller Heat Rejection": self.ct_chiller_HeatRjt_gpm,
                "Tower Source Chiller Heat Rejection (Btu/h)": self.ct_chiller_HeatRjt_btuh,
                "Total WS Heat Extraction Shortfall (Btu/h)": self.total_WS_HeatExt_shortfall,
                "Total WS Heat Rejection Shortfall (Btu/h)": self.total_WS_HeatRjt_shortfall,
                "CHECK:=Simultaneous Heat/Cool Only": self.check_1,
                "CHECK:Simultaneous Heat Only/Chiller": self.check_2,
            }
        )

        return df
