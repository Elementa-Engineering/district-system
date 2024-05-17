from typing import Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, computed_field, validator


class BuildingParameters(BaseModel):
    # adding static inputs
    HW_LoopSTP: pd.Series
    HW_supplyLosses: int
    CHW_LoopSTP: pd.Series
    CHW_supplyLosses: int
    CHW_deltaT_Max: int
    CHW_deltaT_Min: int
    HHW_supply_Temps: pd.Series
    HHW_return_Temps: pd.Series
    HHW_BldgSTP: pd.Series
    DHWMonths: pd.Series
    DHWSetpoint: pd.Series
    buildingDate: pd.Series
    hotWaterMonths: np.ndarray
    # DHW_indices : pd.Series
    DHWmaxApproach: int
    DHWminApproach: int
    HW_returnLosses: int

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
    def DHW_indices(self) -> pd.Series:
        month_to_match = self.buildingDate.dt.month.values

        # Find the index where month matches
        DHW_indices = np.where(month_to_match[:, None] == self.hotWaterMonths)[1]

        # Convert NumPy array to Series
        DHW_indices = pd.Series(DHW_indices)

        return DHW_indices
