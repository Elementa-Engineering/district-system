from typing import Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, computed_field, validator

from districtsystem.building_staticInputs import BuildingParameters


class building_mixing(BaseModel):
    df: pd.DataFrame
    parameters: BuildingParameters

    class MySeries(BaseModel):
        data: dict[str, Union[int, float, str]]  # Dictionary to store Series data

        @validator("data")
        def validate_data(cls, value):
            # Add validation logic here if needed (e.g., check data types, keys)
            return value

    class Config:
        arbitrary_types_allowed = True

    @computed_field
    @property
    def totalSpaceHeating_load(self) -> pd.Series:
        return self.df.groupby("Time Stamp")["Space Heating Load (Btu/h)"].sum()

    @computed_field
    @property
    def totalDHW_load(self) -> pd.Series:
        return self.df.groupby("Time Stamp")["DHW Load (Btu/h)"].sum()

    @computed_field
    @property
    def districtHWSflow(self) -> pd.Series:
        return self.df.groupby("Time Stamp")["District HWS Flow (gpm)"].sum()

    @computed_field
    @property
    def districtHWRT(self) -> pd.Series:
        # check for 0 in flow
        districtHWSflow_is_zero = self.districtHWSflow == 0
        # else the following calc is applied
        bldgHWRTxHWSflow = self.df["District HWRT (°F)"] * self.df["District HWS Flow (gpm)"]
        districtHWRT = (bldgHWRTxHWSflow.groupby(self.df["Time Stamp"]).sum()) / self.districtHWSflow
        return pd.Series(np.where(districtHWSflow_is_zero, 0, districtHWRT))

    @computed_field
    @property
    def districtCHWSflow(self) -> pd.Series:
        return self.df.groupby("Time Stamp")["CHWR Flow (gpm)"].sum()

    @computed_field
    @property
    def districtCHWRT(self) -> pd.Series:
        # check for 0 in flow
        districtHWSflow_is_zero = self.districtCHWSflow == 0
        # calculate average CHWRT
        averageCHWRT = self.df.groupby("Time Stamp")["CHWRT (°F)"].mean()
        # else the following calc is applied
        bldgCHWRTxCHWSflow = self.df["CHWRT (°F)"] * self.df["CHWR Flow (gpm)"]
        districtCHWRT = (bldgCHWRTxCHWSflow.groupby(self.df["Time Stamp"]).sum()) / self.districtCHWSflow
        result = np.where(districtHWSflow_is_zero, averageCHWRT, districtCHWRT)
        return pd.Series(result, index=districtCHWRT.index)

    @computed_field
    @property
    def totalHeating_load(self) -> pd.Series:
        districtHWSflow = self.districtHWSflow.reset_index(drop=True)
        districtHWRT = self.districtHWRT.reset_index(drop=True)
        print("ck", self.districtHWSflow, self.parameters.HW_LoopSTP, self.districtHWRT)
        return districtHWSflow * 500 * (self.parameters.HW_LoopSTP - districtHWRT)

    @computed_field
    @property
    def totalCooling_load(self) -> pd.Series:
        districtCHWSflow = self.districtCHWSflow.reset_index(drop=True)
        districtCHWRT = self.districtCHWRT.reset_index(drop=True)
        return districtCHWSflow * (districtCHWRT - self.parameters.CHW_LoopSTP) * 500
        # return self.districtCHWSflow*(self.districtCHWRT-self.parameters.CHW_LoopSTP)*500

    def compute(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "Total Space Heating Load (Btu/h)": self.totalSpaceHeating_load.reset_index(drop=True),
                "Total DHW Load (Btu/h)": self.totalDHW_load.reset_index(drop=True),
                "District HWS Flow (gpm)": self.districtHWSflow.reset_index(drop=True),
                "District HWRT (°F)": self.districtHWRT.reset_index(drop=True),
                "District CHWS Flow (gpm)": self.districtCHWSflow.reset_index(drop=True),
                "District CHWRT (°F)": self.districtCHWRT.reset_index(drop=True),
                "Total Heating Load (Btu/h)": self.totalHeating_load.reset_index(drop=True),
                "Total Cooling Load (Btu/h)": self.totalCooling_load,
            }
        )

        return df
