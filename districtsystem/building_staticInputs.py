import numpy as np
import pandas as pd
from pydantic import BaseModel, computed_field


class BuildingParameters(BaseModel):
    """
    Represents the parameters for a building.

    Attributes:
        HW_LoopSTP (pd.Series): Series representing the hot water loop setpoint.
        HW_supplyLosses (int): Integer representing the hot water supply losses.
        CHW_LoopSTP (pd.Series): Series representing the chilled water loop setpoint.
        CHW_supplyLosses (int): Integer representing the chilled water supply losses.
        CHW_deltaT_Max (int): Integer representing the maximum chilled water temperature difference.
        CHW_deltaT_Min (int): Integer representing the minimum chilled water temperature difference.
        HHW_supply_Temps (pd.Series): Series representing the hot water supply temperatures.
        HHW_return_Temps (pd.Series): Series representing the hot water return temperatures.
        HHW_BldgSTP (pd.Series): Series representing the hot water building setpoint.
        DHWMonths (pd.Series): Series representing the months for domestic hot water.
        DHWSetpoint (pd.Series): Series representing the setpoint for domestic hot water.
        buildingDate (pd.Series): Series representing the building date.
        hotWaterMonths (np.ndarray): NumPy array representing the months for hot water.
        DHWmaxApproach (int): Integer representing the maximum approach for domestic hot water.
        DHWminApproach (int): Integer representing the minimum approach for domestic hot water.
        HW_returnLosses (int): Integer representing the hot water return losses.
    """

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
    DHWmaxApproach: int
    DHWminApproach: int
    HW_returnLosses: int

    class Config:
        arbitrary_types_allowed = True

    @computed_field
    @property
    def DHW_indices(self) -> pd.Series:
        """
        Returns the indices of the hot water months in the building's date.

        Returns:
            pd.Series: A pandas Series containing the indices of the hot water months.
        """
        month_to_match = self.buildingDate.dt.month.values

        # Find the index where month matches
        DHW_indices = np.where(month_to_match[:, None] == self.hotWaterMonths)[1]

        # Convert NumPy array to Series
        DHW_indices = pd.Series(DHW_indices)

        return DHW_indices
