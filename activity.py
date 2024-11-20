from fitparse import FitFile
from .fancy_package import Task, cstr, Message, ProgressBar
from .metrics import *

from typing import Literal

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

import requests
import time

class Activity:
    """
    All values must be given in SI units.
    Simple class that contains the code to process a bike ride (compute power, drag, remove pauses).
    
    Methods:
    --------
    The following method might be useful for data access, rather than accessing the whole dataframe:
    
        get_data(columns:List[str]) -> pd.DataFrame : returns a deep copy of the dataframe with only the columns specified.
    """
    
    data:pd.DataFrame
    """
    Columns:
    --------
        self.data['time'] : datetime
        self.data['lat'] : float
        self.data['lon'] : float
        self.data['distance'] : float (in m, distance traveled from start)
        self.data['altitude'] : float (in m)
        self.data['heart_rate'] : float (in bpm)
        self.data['speed'] : float (in m/s)
        self.data['rho'] : float (in kg/m^3, air density)
        self.data['drag'] : float (in N, drag force)
        self.data['rolling_resistance'] : float (in N, rolling resistance)
        self.data['kinetic_energy'] : float (in J, kinetic energy)
        self.data['potential_energy'] : float (in J, potential energy)
        self.data['delta_time'] : delta_time (time between two consecutive points)
        self.data['delta_distance'] : float (in m, distance between two consecutive points)
        self.data['delta_altitude'] : float (in m, altitude between two consecutive points)
        self.data['slope'] : float (1 means 100%, slope between two consecutive points)
        self.data['delta_time_seconds'] : float (in s, time between two consecutive points)
        self.data['cumulative_time_seconds'] : float (in s, cumulative time since the start, paused removed)
        self.data['delta_potential_energy'] : float (in W, power due to gravity when going up)
        self.data['delta_kinetic_energy'] : float (in W, change in speed, sum of other powers)
        self.data['watts'] : float (in W, total power, deduced from 3 preceding columns, by watt = kinetic - drag - gravity => take all positive values)
        self.data['braking_power'] : float (in W, power due to braking, negative values from above)
    
    """
    Crr = 0.005 # see wikipedia, 8.3 bar tires bike at 50kph
    Cd = 1.0
    
    
    def __init__(self, fitfile: FitFile, mass:float, height:float, bike_mass:float, age:int, gender:str, recompute_altitude=True) -> None:
        """
        Parameters:
        -----------
            file: str
                fit file usually retrieved from ActivitySet
            mass: float
                mass in kg
            height: float
                height in meters
            bike_mass: float
                mass of the bike in kg
        """
        assert 1000 > mass, "Mass must be given in kg, not grams!"
        self.mass = mass
        assert height < 5, "Size must be given in meters, not cm!"
        self.size = height
        assert 1000 > bike_mass > 0, "Bike mass must be given in kg, not grams, and must be non zero!"
        self.bike_mass = bike_mass
        assert 3 < age < 150, "Age must be given in years!"
        self.age = age
        assert gender in ['m', 'f'], "Gender must be either 'm' or 'f'"
        self.gender = gender
        
        
        
        ##############################
        ### FITFILE INTO DATAFRAME ###
        ##############################
        
        with Task("Reformatting FIT file", new_line=True):
            data = []
            for measure in fitfile.get_messages("record"):
                measure_dict = {}
                for measure_column in measure:
                    measure_dict[measure_column.name] = measure_column.value
                data.append(measure_dict)
            data = pd.DataFrame(data)
            Message.print("Data columns: " + ", ".join(data.columns))
            Message.print("Number of rows: " + str(len(data)))
            
            if len(data)==0:
                Message("Unable todownload activity from Garmin Connect", "!")
                raise(Exception("Empty dataframe. Activity might be corrupted."))
            
            ######################
            ### DEFAULT VALUES ###
            ###################### # in case some are missing / can't be identified.
            
            if not "heart_rate" in data.columns:
                Message("No heart rate data available", "!")
                data["heart_rate"] = 170 # some default value
                
            if not "altitude" in data.columns:
                if not "enhanced_altitude" in data.columns:
                    Message("No altitude data available", "!")
                    data["altitude"] = 0
                else:
                    data["altitude"] = data["enhanced_altitude"]
            
            if not "speed" in data.columns:
                if not "enhanced_speed" in data.columns:
                    Message("No speed data available", "!") # this would be very strange...
                    raise(Exception("Could not find speed data. Cannot continue analysis."))
                else:
                    data["speed"] = data["enhanced_speed"]
            
            data.rename(columns={
                "position_lat": "lat",
                "position_long": "lon",
                "timestamp": "time",
            }, inplace=True)
            
            data = data[
                ["time", "lat", "lon", "distance", "altitude", "heart_rate", "speed"]
            ]
            data["lon"] = data["lon"]/11930465 # type conversion from binary to degrees
            data["lat"] = data["lat"]/11930465
            
        self.data = data
            
        
        with Task("Processing data", new_line=True):
            
            ##################
            ### CHECK DATA ###
            ##################
            
            with Task("Loading data", new_line=False):
                required_columns = ["time", "lat", "lon", "distance", "altitude", "heart_rate", "speed"]
                for col in required_columns:
                    if col not in self.data.columns:
                        Message(f"Missing column {cstr(col):r}", "!")
                        raise ValueError(f"Missing column {col}")
                    
                self.data["time"] = pd.to_datetime(self.data["time"])
            
            with Task("Removing NaN values", new_line=True):
                initial = len(self.data)
                self.data.dropna(inplace=True)
                final = len(self.data)
                Message(f"Removed {cstr(initial - final):y} NaN values (out of {initial})", "?")
                
            ########################
            ### CORRECT ALTITUDE ###
            ########################
            
            # ok here is the deal
            # garmin is bad at computing altitudes, because barometric info depends on wind
            # however it is very difficult to obtain 'enhanced' altitude from lon and lats, because
            # accurate topographic datasets dont really exist (lon lat resolution is not great, about 30m, 
            # about three times the garmin  resolution.#
            
            if recompute_altitude:
                def get_elevation(lats, lons):
                    if isinstance(lats, (int, float)):
                        lats = [lats]
                        lons = [lons]
                    
                    assert len(lats) == len(lons), "lats and lons must have the same length"
                    assert len(lats) > 0, "lats and lons must have at least one element"
                    
                    locations = "|".join([f"{lat},{lon}" for lat, lon in zip(lats, lons)])
                    
                    data = {
                        "locations": locations,
                        "interpolation": "cubic"
                    }
                    
                    url = f"https://api.opentopodata.org/v1/srtm90m"
                    response = requests.get(url, data)
                    if response.status_code == 200:
                        elevation_data = response.json()
                        return [result['elevation'] for result in elevation_data['results']]
                    else:
                        #this should not happen
                        print("\n")
                        print(f"Error: {response.status_code}")
                        print(response.text)
                        print("\n")
                        return None
                
                df = self.data
                with Task("Correcting altitude with OpenTopoData", new_line=True):
                    new_altitude_data = []
                    N_window = 100 # not allowed to request more than 100 positions at once
                    
                    for window in ProgressBar([(i*N_window, (i+1)*N_window) for i in range(len(df)//N_window)] + [(len(df)//N_window * N_window, len(df))], new_line=False):
                        lats, lons = df["lat"].iloc[window[0]:window[1]], df["lon"].iloc[window[0]:window[1]]
                        new_altitude_data.extend(get_elevation(lats, lons))
                        time.sleep(1) # not allowed to request more than 1 request per second
                
                # let's smooth it out a bit, because elevation is rounded to meter here,
                # so sometimes 8% slope comes out of nowhere because of 1m vertical resolution over
                # 12m horizontal resolution.
                dx = self.data['distance'].diff().median()
                window = np.round(200 / dx).astype(int) # 200m window, about 15 measures
                smooth_altitude = savgol_filter(new_altitude_data, window, 3)
                self.data['altitude'] = smooth_altitude
                
            
            #################
            ### CONSTANTS ###
            #################
            
            drag_coefficient = self.Cd
            rho0 = 1.225 # kg/m^3 --> air volumic mass at 0m
            L = 0.0065 # K/m --> temperature gradient
            T0 = 288.15 # K --> temperature at 0m
            R = 287.05 # J/(kg*K) --> gas constant
            g = 9.807 # m/s^2 --> gravity


            #######################
            ### ABSOLUTE VALUES ###
            #######################
            
            with Task("Computing drag", new_line=False):
                projected_frontal_area = 0.0293 * (self.size**0.725) * (self.mass**0.425) + 0.0604
                self.data['rho'] = rho0 * (1 - L * self.data['altitude'] / T0)**(g / (R * L - 1))
                kinetic_pressure = 0.5 * self.data['rho'] * self.data['speed']**2
                self.data['drag'] = drag_coefficient * projected_frontal_area * kinetic_pressure
            
            
            with Task("Computing kinetic energy", new_line=False):
                self.data['kinetic_energy'] = 0.5 * (self.mass + self.bike_mass) * self.data['speed']**2
            with Task("Computing potential energy", new_line=False):
                self.data['potential_energy'] = (self.mass + self.bike_mass) * 9.81 * self.data['altitude']
            
            
            ####################
            ### DELTA VALUES ###
            ####################
            
            with Task("Computing delta values", new_line=False):
                for col in ["time", "distance", "altitude", "speed", "kinetic_energy", "potential_energy"]:
                    self.data[f"delta_{col}"] = self.data[col].diff()
                self.data = self.data.iloc[1:].copy(deep=True) # first column
                
                self.data['slope'] = self.data['delta_altitude'] / self.data['delta_distance'] # 100 * slope is slope in % # if you do pause in garmin, distances stop, and if you resume later at different altitude, you get a hudge slope, so we need to be careful with that
            self.data["delta_time_seconds"] = self.data["delta_time"].dt.total_seconds()
            
            with Task("Computing rolling resistance", new_line=False): # needed slope for that
                Crr = self.Crr 
                self.data['rolling_resistance'] = Crr * (self.mass + self.bike_mass) * g * np.cos(np.arctan(self.data['slope']))
                
            
            ############################
            ### PAUSE IDENTIFICATION ###
            ############################
            
            with Task("Removing pauses from the ride", new_line=True):
                
                intitial_length = len(self.data)
                mask_to_remove = (
                    (self.data['delta_distance'] < 1) & (self.data["delta_time_seconds"] > 10) # no movement (less than 1m) over 10s.
                ) | (
                    (self.data['delta_distance'] < 1) & (self.data["delta_distance"] < self.data["delta_time_seconds"] * 1) # no movement (less than 10cm) over and average speed of less than 3.6 km/h
                )
                
                self.data = self.data[~mask_to_remove].copy(deep=True)
                
                # remove data where speed, distance delta and time delta don't match
                mask_to_remove = (
                    (self.data["delta_distance"] - self.data["delta_time_seconds"] * self.data["speed"]).abs() > self.data["delta_distance"] / 2 # tolerate 50% error
                )
                self.data = self.data[~mask_to_remove].copy(deep=True)
            
            
                final_length = len(self.data)
                Message(f"Removed {cstr((intitial_length - final_length)/intitial_length, format_spec='.2%'):y} of the data", "?")
            self.data["cumulative_time_seconds"] = self.data["delta_time_seconds"].cumsum()
            
            with Task("Removing Garmin bugs", new_line=True):
                mask_to_remove = self.data["delta_time_seconds"] > 5 * self.data["delta_time_seconds"].std() + self.data["delta_time_seconds"].median()
                mask_to_remove |= self.data["slope"].abs() > 0.4 # 40% slope is very unlikely... this is probably a bug
                
                initial_length = len(self.data)
                self.data = self.data[~mask_to_remove].copy(deep=True)
                final_length = len(self.data)
                Message(f"Removed {cstr((initial_length - final_length)/initial_length, format_spec='.2%'):y} of the data", "?")
                
            
            
            #########################
            ### POWER COMPUTATION ###
            #########################
            
            with Task("Computing Watts", new_line=False):
                energy_delta = self.data["delta_kinetic_energy"] + self.data["delta_potential_energy"]
                drag_power = - self.data["drag"] * self.data["speed"]
                rolling_resistance_power = - self.data["rolling_resistance"] * self.data["speed"]
                
                self.data["watts"] = energy_delta / self.data["delta_time_seconds"] - drag_power - rolling_resistance_power # power(pedalage) + power(drag) = energy / time
                self.data["watts"] = self.data["watts"].rolling(window=5, min_periods=1, center=True).median() # smooth the power
                # where watt is nan, set to 0
                self.data.loc[self.data["watts"].isna(), "watts"] = 0
                
                # negative watt means braking!
                self.data["braking_power"] = self.data["watts"].copy(deep=True)
                self.data.loc[self.data["watts"] < 0, "watts"] = 0
                self.data.loc[self.data["braking_power"] > 0, "braking_power"] = 0
                
            # finally we do as if the pauses were never there
            self.data.reset_index(drop=True, inplace=True)
            
            
            ##############################
            ### SPEED AJUSTED TO SLOPE ###
            ##############################
            
            with Task("Computing speed adjusted to slope", new_line=False):
                # this is no easy task, we want to solve:
                # P = [drag/v0^2] * v^3 + [rolling_resistance] * v
                # we use newton's method to solve this equation
                
                def root_deg_3(D, R, P):
                        roots = np.roots([D, 0, R, -P])
                        sorted_roots = [r for r in roots if r.real==0 or (r.imag / r.real < 1e-3 and r.real > 0)]
                        max_real_part = max(sorted_roots, key=lambda r: r.real)
                        return max_real_part.real
                
                self.data['adj_speed'] = .0
                for i, row in self.data.iterrows():
                    D = 0.5 * row['rho'] * projected_frontal_area * drag_coefficient
                    R = row['rolling_resistance']
                    P = row['watts']
                    
                    self.data.loc[i, 'adj_speed'] = root_deg_3(D, R, P)
                    
                self.data.loc[
                    self.data['adj_speed'] < self.data['speed'], 'adj_speed'
                ] = np.nan # remove values in descent where speed is higher than it should be
                
            # let's try to make them equal on flat
            data_flat = self.data[self.data['slope'].abs() < 0.01]
            speed_ratio = data_flat['speed'].mean() / data_flat['adj_speed'].mean()
            Message(f"Adjusted speed anomalous ratio (should be <1, but relatively close to 1): {cstr(speed_ratio, '.2f'):y}", "?")
            speed_ratio = min(1, speed_ratio)
            self.data['adj_speed'] = self.data['adj_speed'] * speed_ratio
            
            
            
            
    def get_data(self, columns:list = None) -> pd.DataFrame:
        """
        Returns a deep copy of the dataframe, with only specified columns (all of them if None).
        
        Columns:
        --------
        self.data['time'] : datetime
        self.data['lat'] : float
        self.data['lon'] : float
        self.data['distance'] : float (in m, distance traveled from start)
        self.data['altitude'] : float (in m)
        self.data['heart_rate'] : float (in bpm)
        self.data['speed'] : float (in m/s)
        self.data['rho'] : float (in kg/m^3, air density)
        self.data['drag'] : float (in N, drag force)
        self.data['kinetic_energy'] : float (in J, kinetic energy)
        self.data['potential_energy'] : float (in J, potential energy)
        self.data['delta_time'] : delta_time (time between two consecutive points)
        self.data['delta_distance'] : float (in m, distance between two consecutive points)
        self.data['delta_altitude'] : float (in m, altitude between two consecutive points)
        self.data['slope'] : float (1 means 100%, slope between two consecutive points)
        self.data['delta_time_seconds'] : float (in s, time between two consecutive points)
        self.data['cumulative_time_seconds'] : float (in s, cumulative time since the start, paused removed)
        self.data['gravity_power'] : float (in W, power due to gravity when going up)
        self.data['kinetic_power'] : float (in W, change in speed, sum of other powers)
        self.data['drag_power'] : float (in W, power due to drag)
        self.data['watts'] : float (in W, total power, deduced from 3 preceding columns, by watt = kinetic - drag - gravity => take all positive values)
        self.data['braking_power'] : float (in W, power due to braking, negative values from above)
    
        """
        if columns is None:
            return self.data.copy(deep=True)
        else:
            return self.data[columns].copy(deep=True)

    
    
    @staticmethod
    def from_file(file:str, mass:float, height: float, bike_mass:float, age: int, gender:Literal['m', 'l'], recompute_altitude=True) -> 'Activity':
        """
        Parameters:
        -----------
            file: str
                path to the .fit file
            mass: float
                mass in kg
            height: float
                height in meters
            bike_mass: float
                mass of the bike in kg
        """
        with open(file, 'rb') as f:
            fitfile = FitFile(f)
    
            return Activity(fitfile, mass, height, bike_mass, age, gender, recompute_altitude) # needs to be done while the file is still open!
    
    @staticmethod
    def get_metrics(activity:'Activity') -> dict:
        """
        
        """
        
        # compute elevation gain for a smoothed profile over a 200m resolution
        window_length = 200
        dx = activity.data['distance'].diff().median()
        window = int(window_length / dx)
        
        smooth_elevation_gain = np.diff(savgol_filter(activity.data['altitude'], window, 3))
        df = activity.get_data(columns=['time', 'watts', 'delta_time_seconds', 'cumulative_time_seconds', 'heart_rate'])
        return {
            "duration_s": activity.data['cumulative_time_seconds'].iloc[-1],
            "distance_km": activity.data['distance'].iloc[-1] / 1000,
            "elevation_gain_m": smooth_elevation_gain[smooth_elevation_gain > 0].sum(),
            "average_speed_kmh": activity.data['speed'].mean() * 3.6,
            "max_speed_kmh": activity.data['speed'].max() * 3.6,
            "slope_adjusted_average_speed_kmh": activity.data['adj_speed'].mean() * 3.6,
            "average_power_w": activity.data['watts'].mean(),
            "ftp_w": get_ftp(df),
            "ftp_wkg": get_ftp(df) / activity.mass,
            "ppo_w": get_ppo(df),
            "vo2max_mlkgmin": get_vo2max(df, activity.mass, activity.gender),
            "normalized_power_w": get_normalized_power(df),
            "intensity_factor": get_intensity_factor(df),
            "training_stress_score": get_training_stress_score(df, activity.mass),
            "normalized_training_stress_score": get_training_stress_score(df, activity.mass, absolute=True),
            "average_heart_rate_bpm": activity.data['heart_rate'].mean(),
            "max_heart_rate_bpm": activity.data['heart_rate'].max(),
            "heart_rate_q95_bpm": activity.data['heart_rate'].quantile(0.95),
            "calories_kcal": get_calories(df, activity.mass, activity.age),
            "efficiency_%": get_efficiency(df, activity.mass, activity.age) * 100
        }
    