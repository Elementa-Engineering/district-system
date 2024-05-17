import pandas as pd
from pydantic import BaseModel, computed_field


class CUP(BaseModel):
    timeStamp: pd.DataFrame
    hotTank_schedule: pd.DataFrame
    coldTank_schedule: pd.DataFrame
    totalHeating_load: pd.Series
    totalCooling_load: pd.Series
    districtHWRT: pd.Series = None
    districtCHWRT: pd.Series = None
    districtHWSflow: pd.Series = None
    districtCHWSflow: pd.Series = None
    HW_districtSTP: pd.Series = None
    CHW_districtSTP: pd.Series = None
    HP_HW_gpm: pd.Series = None
    HP_CHWST: pd.Series = None
    HP_CHW_gpm: pd.Series = None
    TES_H_tempOut: pd.Series = None
    TES_H_flowOut: pd.Series = None
    TES_C_flowOut: pd.Series = None
    TES_C_tempOut: pd.Series = None
    TES_C_flowinto: pd.Series = None
    TES_H_flowinto: pd.Series = None
    boiler_HWflow_gpm: pd.Series = None
    chiller_CHWSflow_gpm: pd.Series = None

    class Config:
        arbitrary_types_allowed = True

    def is_on(self, tank_schedule, month, hour):
        # loc is used to get the valu at the month and hour of the schedule using "labels- row or col name"
        value = tank_schedule.loc[tank_schedule["Month"] == month, hour]
        return value.iloc[0] == 1

    @computed_field(return_type=pd.Series)
    @property
    def HW_charging(self) -> pd.Series:
        result = []
        for ts in self.timeStamp["Date and Time"]:
            month = ts.month
            hour = ts.hour
            # print("ts",month, hour)
            result.append(self.is_on(self.hotTank_schedule, month, hour))
        # print(df)
        return pd.Series(result)

    @computed_field
    @property
    def CHW_charging(self) -> pd.Series:
        result = []
        for ts in self.timeStamp["Date and Time"]:
            month = ts.month
            hour = ts.hour

            result.append(self.is_on(self.coldTank_schedule, month, hour))
        # print(df)
        return pd.Series(result)

    @computed_field
    @property
    def shiftCount(self) -> pd.Series:
        value = self.timeStamp["Date and Time"].dt.dayofyear - 1
        return value

    def predictedDayLoad(self, shiftCount, load) -> pd.Series:
        data = {"shiftCount": shiftCount, "load": load}
        df = pd.DataFrame(data)

        # initiate empty series to store results
        result_series = pd.Series(index=shiftCount.index)

        for value in shiftCount.unique():
            # filter to every shiftcount value
            filtered_df = df[df["shiftCount"] == value]
            summed_value = filtered_df["load"].sum()

            result_series[shiftCount == value] = summed_value
        return result_series

    @computed_field
    @property
    def predictedDay_heating(self) -> pd.Series:
        x = self.predictedDayLoad(self.shiftCount, self.totalHeating_load)
        return x

    @computed_field
    @property
    def predictedDay_cooling(self) -> pd.Series:
        x = self.predictedDayLoad(self.shiftCount, self.totalCooling_load)
        return x

    def predictedDayLoad_shift(self, shiftCharging, shiftCount, load) -> pd.Series:
        data = {"shiftCharging": shiftCharging, "shiftCount": shiftCount, "load": load}
        df = pd.DataFrame(data)

        # initiate empty series to store results
        result_series = pd.Series(index=shiftCount.index)

        # this is working but write better code to not use loop to assign value to every value
        for value in shiftCount.unique():
            filtered_df = df[(df["shiftCount"] == value) & (df["shiftCharging"] is True)]
            summed_value = filtered_df["load"].sum()
            result_series[shiftCount == value] = summed_value

        return result_series

    @computed_field
    @property
    def predictedDay_heating_shift(self) -> pd.Series:
        x = self.predictedDayLoad_shift(self.HW_charging, self.shiftCount, self.totalHeating_load)
        return x

    @computed_field
    @property
    def predictedDay_cooling_shift(self) -> pd.Series:
        x = self.predictedDayLoad_shift(self.CHW_charging, self.shiftCount, self.totalCooling_load)
        return x

    # checks total hours the tank is on
    def total_on(self, tank_schedule, month) -> pd.Series:
        # loc is used to get the valu at the month and hour of the schedule using "labels- row or col name"
        value = tank_schedule.loc[tank_schedule["Month"] == month, "Total"]
        return value.iloc[0]

    @computed_field
    @property
    def HL_totalShiftHours(self) -> pd.Series:
        result = []
        for ts in self.timeStamp["Date and Time"]:
            month = ts.month

            result.append(self.total_on(self.hotTank_schedule, month))
        # print(df)
        return result

    @computed_field
    @property
    def CL_totalShiftHours(self) -> pd.Series:
        result = []
        for ts in self.timeStamp["Date and Time"]:
            month = ts.month

            result.append(self.total_on(self.coldTank_schedule, month))
        # print(df)
        return result

    ################# result to df -- compute one #############
    def compute_CUP(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "Hot Load Shift Charging": self.HW_charging,
                "Cold Load Shift Charging": self.CHW_charging,
                "Hot Load Shift Hours": self.HL_totalShiftHours,
                "Cold Load Shift Hours": self.CL_totalShiftHours,
                "Shift Count": self.shiftCount,
                "Predicted Day's Heating Load (Btu/h)": self.predictedDay_heating,
                "Predicted Day's Cooling Load (Btu/h)": self.predictedDay_cooling,
                "Predicted Heating Load in Load Shift Window (Btu/h)": self.predictedDay_heating_shift,
                "Predicted Cooling Load in Load Shift Window (Btu/h)": self.predictedDay_cooling_shift,
            }
        )

        return df

    #################### CUP calc- second half #############################

    # =((K3-I3)*L3+(K3-I3)*W3)*500-((K3-P3)*Q3+(K3-U3)*V3+(K3-Z3)*AA3)*500
    @computed_field
    @property
    def cooling_shortfall(self) -> pd.Series:
        return (
            (self.districtCHWRT - self.CHW_districtSTP) * self.districtCHWSflow
            + (self.districtCHWRT - self.CHW_districtSTP) * self.TES_C_flowinto
        ) * 500 - (
            (self.districtCHWRT - self.HP_CHWST) * self.HP_CHW_gpm
            + (self.districtCHWRT - self.TES_C_tempOut) * self.TES_C_flowOut
            + (self.districtCHWRT - self.CHW_districtSTP) * self.chiller_CHWSflow_gpm
        ) * 500

    # =((H3-J3)*M3+(H3-J3)*T3)*500-((N3-J3)*O3+(R3-J3)*S3+(X3-J3)*Y3)*500

    @computed_field
    @property
    def heating_shortfall(self) -> pd.Series:
        # return (((self.HW_districtSTP-self.districtHWRT)*self.districtHWSflow+(self.HW_districtSTP-self.districtHWRT)*self.TES_H_flowinto)*500-((self.HW_districtSTP-self.districtHWRT)*
        #         self.HP_HW_gpm+(self.TES_H_tempOut-self.districtHWRT) *self.TES_H_flowOut+(self.HW_districtSTP-self.districtHWRT)*self.boiler_HWflow_gpm)*500)                                                                                                       )
        district_stp_minus_hwrt = self.HW_districtSTP - self.districtHWRT
        first_term = (
            district_stp_minus_hwrt * self.districtHWSflow + district_stp_minus_hwrt * self.TES_H_flowinto
        ) * 500
        second_term = (
            district_stp_minus_hwrt * self.HP_HW_gpm
            + (self.TES_H_tempOut - self.districtHWRT) * self.TES_H_flowOut
            + district_stp_minus_hwrt * self.boiler_HWflow_gpm
        ) * 500
        return first_term - second_term

    @computed_field
    @property
    def CUP_HWRflow(self) -> pd.Series:
        return self.districtHWSflow + self.TES_H_flowinto

    @computed_field
    @property
    def CUP_CHWRflow(self) -> pd.Series:
        return self.districtCHWSflow + self.TES_C_flowinto

    @computed_field
    @property
    def CUP_HWRtemp(self) -> pd.Series:
        try:
            result = (
                self.districtHWRT * self.districtHWSflow + self.TES_H_tempOut * self.TES_H_flowinto
            ) / self.CUP_HWRflow
        except Exception:
            result = self.districtHWRT
        return result

    @computed_field
    @property
    def CUP_CHWRtemp(self) -> pd.Series:
        try:
            result = (
                self.districtCHWRT * self.districtCHWSflow + self.TES_C_tempOut * self.TES_C_flowinto
            ) / self.CUP_CHWRflow
        except ZeroDivisionError:
            result = self.districtCHWRT
        return result

    @computed_field
    @property
    def CUP_HWST(self) -> pd.Series:
        try:
            result = (
                self.HW_districtSTP * self.HP_HW_gpm
                + self.TES_H_tempOut * self.TES_H_flowOut
                + self.HW_districtSTP * self.boiler_HWflow_gpm
            ) / self.CUP_HWRflow
        except ZeroDivisionError:
            result = self.HW_districtSTP
        return result

    @computed_field
    @property
    def CUP_CHWST(self) -> pd.Series:
        # =IFERROR((P3*Q3+U3*V3+Z3*AA3)/AN3,I3)
        try:
            result = (
                self.HP_CHWST * self.HP_CHW_gpm
                + self.TES_C_tempOut * self.TES_C_flowOut
                + self.CHW_districtSTP * self.chiller_CHWSflow_gpm
            ) / self.CUP_CHWRflow
        except ZeroDivisionError:
            result = self.CHW_districtSTP
        return result

    @computed_field(return_type=pd.Series)
    @property
    def max_diff(self: BaseModel) -> pd.Series:
        return self.CUP_CHWRtemp - self.districtCHWRT

    ################# result to df -- compute one #############
    def compute_CUP_two(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "Cooling Shortfall (Btu/h)": self.cooling_shortfall,
                "Heating Shortfall (Btu/h)": self.heating_shortfall,
                "Hot Load Shift Charging": self.HW_charging,
                "Cold Load Shift Charging": self.CHW_charging,
                "Hot Load Shift Hours": self.HL_totalShiftHours,
                "Cold Load Shift Hours": self.CL_totalShiftHours,
                "Shift Count": self.shiftCount,
                "Predicted Day's Heating Load (Btu/h)": self.predictedDay_heating,
                "Predicted Day's Cooling Load (Btu/h)": self.predictedDay_cooling,
                "Predicted Heating Load in Load Shift Window (Btu/h)": self.predictedDay_heating_shift,
                "Predicted Cooling Load in Load Shift Window (Btu/h)": self.predictedDay_cooling_shift,
                "CUP HWR Flow (gpm)": self.CUP_HWRflow,
                "CUP CHWR Flow (gpm)": self.CUP_CHWRflow,
                "CUP HWR Temperature (°F)": self.CUP_HWRtemp,
                "CUP CHWR Temperature (°F)": self.CUP_CHWRtemp,
                "CUP HWST (°F)": self.CUP_HWST,
                "CUP CHWST (°F)": self.CUP_CHWST,
                "Max diff between District CHWRT and CUP CHWRT": self.max_diff,
            }
        )

        return df
