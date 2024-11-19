

import numpy as np
import pandas as pd

from scipy.signal import savgol_filter
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import datetime

import requests
import geopy

class ClimbSet:
    scale = 1000 #m
    slope_treshold = 0.02 
    minimal_difficulty_score = 30
    
    def __init__(self, data:pd.DataFrame):
        
        data = data.dropna().copy(deep=True)
        
        required_columns = ["distance", "altitude", "slope", "lon", "lat", "delta_time_seconds"]
        assert all([col in data.columns for col in required_columns]), f"Missing required columns. Are required: {required_columns}"
        data = data[required_columns]
        
        self.data = data.dropna().reset_index(drop=True)
        self.climb_candidates = []
        self.climb_start_candidates = []
        self.climbs = []

        #print("Data smooth")
        self.smooth_data() # remove high frequency features, noise
        #self.show()
        
        #print("Find maxima and minima")
        self.find_maxima_minima() 
        #self.show()
        
        #print("Find climb candidates, high enough maxima")
        self.find_climb_candidates() # find local maxima that are significantly above neighbouring points
        #self.show()
        
        #print("Merge climb candidates, no local minima inbetween")
        self.merge_candidates() # if two condidates are very close, it can happen that there is no local minima inbetween. this means that both candidates are probably part of the same climb
        #self.show()
        
        #print("Find start of climbs, no double local minimas")
        self.merge_start_candidates() # for each candidate (local maximum), we want to find the start of the climb. candidates are, for now, one of the previous local minima
        #self.show()
        
        #print("Extract climbs")
        self.extract_climbs() # for each climb, we extract the corresponding dataset
        #self.show()
        
        self.cut_climbs() # for each climb, we find the exact start by looking at the slope
        #self.show()
        
        self.clean_climbs() # remove climbs that are too flat, too short
        #self.show()
    
    
    def smooth_data(self):
        dx = self.data["distance"].diff().median()
        self.window = int(self.scale/dx)
        
        self.data["altitude"] = savgol_filter(self.data["altitude"], self.window, 3)
        self.data["slope"] = savgol_filter(self.data["slope"], self.window, 3)
        
    
    def find_maxima_minima(self):
        rolling_max_altitude = self.data["altitude"].rolling(window=2*self.window, center=True, min_periods=1).max() # 2*window because the climb is actually before, not after, but after we want to know if clim continues
        self.data["local_max"] = (self.data["altitude"] == rolling_max_altitude)
        
        rolling_min_altitude = self.data["altitude"].rolling(window=2*self.window, center=True, min_periods=1).min() # uefull to find the start of the climb
        self.data["local_min"] = (self.data["altitude"] == rolling_min_altitude)
        
    
    def find_climb_candidates(self):
        # we want to remove local maxima too close in terms of altitude comapred to the closest previous local minima
        # meaning it is not a real climb, it is too small to be one
        
        local_minima_indeces = self.data[self.data["local_min"]].index
        local_maxima_indeces = self.data[self.data["local_max"]].index
        
        climb_candidates = []
        for max_idx in local_maxima_indeces:
            if max_idx < min(local_minima_indeces):
                continue # the first local max, if it is before the first local min, it just means that the sarting point is above the next points => the ride started with a decent
            closest_previous_minima = local_minima_indeces[local_minima_indeces < max_idx].max()
            
            if self.data["altitude"][max_idx] - self.data["altitude"][closest_previous_minima] > self.slope_treshold * self.scale:
                climb_candidates.append(max_idx)
        
        self.climb_candidates = climb_candidates
                
    
    def merge_candidates(self):
        
        for _ in range(len(self.climb_candidates)): # greedy, we iterate many times
            # we delete one climb at a time, so maximum len(self.climb_candidates) iterations
            
            for i in range(len(self.climb_candidates)-1): # find who to remove
                nbr_local_minima_inbetween = pd.Series(self.data["local_min"][self.climb_candidates[i]:self.climb_candidates[i+1]]).sum()
                
                if nbr_local_minima_inbetween == 0:
                    # we want to merge i and i+1
                    # we want to keep only the highest one
                    
                    if self.data["altitude"][self.climb_candidates[i]] > self.data["altitude"][self.climb_candidates[i+1]]:
                        self.climb_candidates.pop(i+1)
                    else:
                        self.climb_candidates.pop(i)
                    
                    break # we did one deletion, let's start over with updates candidates list
            
            
    def merge_start_candidates(self):
        
        # we want only one local minima for each candidate
        
        climb_start_candidates = []
        
        for i in range(len(self.climb_candidates)):
            local_maximum = self.climb_candidates[i]
            previous_local_maximum = self.climb_candidates[i-1] if i > 0 else 0 # we want only one local minimum between them (the one of smallest altitude)
            
            all_local_minima_inbetween = pd.Series(self.data.index[self.data["local_min"]])[
                pd.Series(self.data.index[self.data["local_min"]]).between(
                    previous_local_maximum,
                    local_maximum
                )
            ]
            
            # find local_minimum with the smallest altitude
            climb_start_candidates.append(min(all_local_minima_inbetween, key=lambda x: self.data["altitude"][x]))

        self.climb_start_candidates = climb_start_candidates
    
    
    def extract_climbs(self):
        
        climbs = []
        for i in range(len(self.climb_candidates)):
            climb = self.data[self.climb_start_candidates[i]:self.climb_candidates[i]]
            
            # lets first reset the index
            climb = climb.reset_index(drop=True) # we loose the info about index here, but we can find them back with the distance column!
            
            # let's check that each climb is steep enough (at least 1% of 1km somewhere)
            rolling_slope = climb["slope"].rolling(window=self.window, center=True, min_periods=1).median()
            if (rolling_slope > self.slope_treshold).sum() == 0:
                continue
            
            climbs.append(climb.copy(deep=True))
        self.climbs = climbs
        
       
    
    def cut_climbs(self):
        
        for i, climb in enumerate(self.climbs):
            climb:pd.DataFrame
            
            # let's maximize diffiuclty score
            best_idx = 0
            best_score = 0
            
            for idx in range(1, len(climb)-1):
                temp_climb = climb.iloc[idx:]
                score = ClimbSet._difficulty_score(temp_climb) 
                
                if score > best_score:
                    best_score = score
                    best_idx = idx
            
            self.climbs[i] = climb.iloc[best_idx:].copy(deep=True)
    
    
    def clean_climbs(self):
        
        climbs = []
        
        for climb in self.climbs:
            climb:pd.DataFrame
            
            
            category = ClimbSet.climb_category(climb)
            if category == 5:
                continue
            
            climbs.append(climb)
        
        self.climbs = climbs
        
            
    
    def get_climbs(self):
        return self.climbs
    
    def get(self, i:int):
        return self.climbs[i]

    
    
    def show(self):
        plt.figure(figsize=(15, 5))
        plt.title("Elevation profile and search for climbs")
        plt.plot(self.data["distance"], self.data["altitude"], label="altitude")
        
        if "local_max" in self.data.columns:
            plt.scatter(self.data["distance"][self.data["local_max"]], self.data["altitude"][self.data["local_max"]], c="red", label="local max", s=20, zorder = 10)
            plt.scatter(self.data["distance"][self.data["local_min"]], self.data["altitude"][self.data["local_min"]], c="green", label="local min", s=20, zorder = 10)
        
        if self.climb_candidates:
            plt.scatter(self.data["distance"][self.climb_candidates], self.data["altitude"][self.climb_candidates], c="blue", label="climb candidates", s=12, zorder = 11)
        
        if self.climb_start_candidates:
            plt.scatter(self.data["distance"][self.climb_start_candidates], self.data["altitude"][self.climb_start_candidates], c="yellow", label="climb start candidates", s=12, zorder = 11)
            
        if self.climbs:
            for climb in self.climbs:
                plt.plot(climb["distance"], climb["altitude"], color='darkblue')
            plt.plot([], [], label="climbs", color='darkblue')
        
        plt.legend()
        plt.xlabel("Distance (m)")
        plt.ylabel("Elevation (m)")
        plt.show()
        
    
    
    @staticmethod
    def _difficulty_score(climb:pd.DataFrame, slope_power:float=2, distance_power:float=1) -> float:
        required_columns = ["distance", "altitude", "slope"]
        assert all([col in climb.columns for col in required_columns]), "Missing required columns. Distance, altitude and slope are required."
        
        climb = climb[required_columns]
        
        average_slope = (climb["altitude"].iloc[-1] - climb["altitude"].iloc[0]) / (climb["distance"].iloc[-1] - climb["distance"].iloc[0])
        average_slope*=100 # convert into %
        distance_km = (climb["distance"].iloc[-1] - climb["distance"].iloc[0]) / 1000
        
        if average_slope<0: # show not happen but just in case
            return 0
        
        return average_slope**slope_power * distance_km**distance_power
        
        
    @staticmethod
    def climb_category(climb:pd.DataFrame) -> int:
        """
        0: HC
        1: category 1
        2: category 2
        3: category 3
        4: category 4
        5: flat (less than minimal_difficulty_score, defaults to 40)
        """
        score = ClimbSet._difficulty_score(climb)
        
        if score > 600:
            return 0
        elif score > 300:
            return 1
        elif score > 150:
            return 2
        elif score > 75:
            return 3
        elif score > ClimbSet.minimal_difficulty_score:
            return 4
        else:
            return 5
        
    @staticmethod
    def find_climb_location(climb:pd.DataFrame):
        
        require_columns = ["lon", "lat"]
        assert all([col in climb.columns for col in require_columns]), "Missing required columns. lon and lat are required."
        lon, lat = climb["lon"].iloc[-1], climb["lat"].iloc[-1]
        
        gelocator = geopy.Nominatim(user_agent="climb_finder")
        location_tokens = str(gelocator.reverse((lat, lon), language="en").address).split(',')
        return location_tokens[0].strip() + ' - ' + location_tokens[1].strip()
    
    
    @staticmethod
    def show_climb(climb:pd.DataFrame):

        required_columns = ["distance", "altitude", "slope", "lon", "lat", "delta_time_seconds"]
        assert all([col in climb.columns for col in required_columns]), "Missing required columns. Are required: distance, altitude, slope, lon, lat"
        
        climb = climb[required_columns].copy(deep=True)
        climb["distance"] -= climb["distance"].iloc[0]
        
        climb_distance = climb["distance"].iloc[-1]
        climb_height = climb["altitude"].iloc[-1] - climb["altitude"].iloc[0]
        climb_time = climb["delta_time_seconds"].sum()
        avg_speed_kmh = climb_distance / climb_time * 3.6
        
        # 200m boxes
        if climb_distance < 4000:
            scale = 200
        elif climb_distance < 10000:
            scale = 500
        elif climb_distance < 20000:
            scale = 1000
        else:
            scale = 2000
            

        
        n_boxes = int(climb["distance"].iloc[-1] / scale)
        boxes = [[scale*i, scale*(i+1)] for i in range(n_boxes)]
        boxes[-1][1] = climb["distance"].iloc[-1]
        
        # avoid gap because 200*i doesn't correspond to distance point
        subclimbs = []
        for box in boxes:
            if len(subclimbs)>0:
                box[0] = subclimbs[-1]["distance"].iloc[-1]
                
            subclimb = climb[climb["distance"].between(box[0], box[1], inclusive="both")].copy(deep=True)
            subclimbs.append(subclimb)
        
        category = f"Categorie {ClimbSet.climb_category(climb)}" if ClimbSet.climb_category(climb) != 0 else "Hors Categorie"
        score = np.round(ClimbSet._difficulty_score(climb)).astype(int)
        
        
        cmap = LinearSegmentedColormap.from_list(
            "mycmap", [(0, "green"), (0.04, "yellow"), (0.08, "orange"), (0.12, "red"), (0.16, "brown"), (0.20, "black"), (1,"black")]
        )
        
        plt.figure(figsize=(15, 8))
        plt.title(
            f"{ClimbSet.find_climb_location(climb)}\n" +\
                f"{category} ({score})\n" +\
                    f"{climb_height:.0f}m - {climb_distance/1000:.1f}km\n" +\
                        f"{datetime.timedelta(seconds=climb_time)} - {avg_speed_kmh:.1f}km/h"
        )
        
        for subclimb in subclimbs:
            average_slope = (subclimb["altitude"].iloc[-1] - subclimb["altitude"].iloc[0]) / (subclimb["distance"].iloc[-1] - subclimb["distance"].iloc[0])
            
            if average_slope < 0.01:
                plt.fill_between(subclimb["distance"], subclimb["altitude"], color="gray")
                continue
                
            plt.fill_between(subclimb["distance"], subclimb["altitude"], color=cmap(average_slope))
            
            alt_offset = climb_height / 20
            distance_offset = scale / 10
            
            
            plt.text(subclimb["distance"].iloc[0] + distance_offset, subclimb["altitude"].iloc[0] - alt_offset, f"{int(average_slope*100)}%", fontsize=12, fontweight="bold", color="white")
            
        plt.plot(climb["distance"], climb["altitude"], color="white")
        plt.xlim(0, climb["distance"].iloc[-1])
        plt.ylim(climb["altitude"].min()-alt_offset*2, climb["altitude"].max()+ alt_offset*2)
        
        new_xticks = [box[0] for box in boxes] + [boxes[-1][1]]
        plt.xticks(new_xticks, [f"{x/1000:.1f}" for x in new_xticks])
        
        plt.xlabel("Distance (km)")
        plt.ylabel("Elevation (m)")
        
        
    