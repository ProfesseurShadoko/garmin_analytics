

# --------------- #
# !-- Imports --! #
# --------------- #

from oakley import *
import datetime
import os
import fitparse

from typing import Literal
import geopy

import numpy as np
import datetime

from .activity import Activity
from oakley import XConfig

assert "GARMIN" in os.environ, "Please set the GARMIN environment variable to the Garmin data directory."
garmin_directory = os.environ["GARMIN"]


# ------------------ #
# !-- City Cache --! #
# ------------------ #

cache_filepath = os.path.join(os.path.dirname(__file__), "city_cache.json")
city_cache = XConfig(cache_filepath)



class ActivitySet:

    city_cache = city_cache

    def __init__(self):
        """
        Loads all activities from the Garmin data directory and
        extracts metadata from each activity.
        """
        # 1. Find all acitivites in the Garmin data directory
        garmin_dir = garmin_directory
        activity_files = [os.path.join(garmin_dir, f) for f in os.listdir(garmin_dir) if f.endswith(".fit")]
        
        # 2. Get metadata for each file name
        self.files = {}
        with Task(f"Loading metadata from {len(activity_files)} files"):
            for filepath in ProgressBar(activity_files):
                self.files[filepath] = self._activity_metadata_from_file(filepath)
        
        # 3. Sort by start time and keep only the last `n_load` activities
        self.files = dict(sorted(self.files.items(), key=lambda x: x[1]["start_time"], reverse=True))
        
        # 4. Load cities for each activity
        with Task("identifying cities for each activity"):
            for filepath, metadata in ProgressBar(self.files.items()):
                lon = metadata["start_position_long"]
                lat = metadata["start_position_lat"]
                city = self._find_city(lon, lat)
                self.files[filepath]["city"] = city

    def display(self):
        """
        Displays the available activites with enough 
        information to identify them (date, city, distance, d+).
        """

        def format_information(metadata):
            date = metadata["start_time"].strftime("%Y-%m-%d")
            city = metadata["city"]
            distance = np.round(metadata["total_distance"] / 1000, 0).astype(int)  # convert to km
            ascent = np.round(metadata["total_ascent"], 0).astype(int)
            avg_speed = metadata["avg_speed"]
            return city, f"({date}) --> {cstr(f'{distance:3d}'):b} km, {cstr(f'{avg_speed:.1f}'):r} km/h, {cstr(f'{ascent:4d}'):y} m d+"
        
        n_digits = len(str(len(self.files)))
        display_dict = {
            f"({i+1:>{n_digits}d}) {city}": info for i, (city, info) in enumerate([format_information(metadata) for metadata in self.files.values()])
        }
        Message(f"Available activities:", "#").list(display_dict)

    
    def activity(
            self,
            index:int,
            mass: float,
            height: float,
            bike_mass: float,
            age:int,
            gender: Literal["f", "m"],
            recompute_altitude: bool = True
        ) -> Activity:
        """
        Parameters
        ----------
        index : int
            The index of the activity to retrieve (1-based).
        mass : float
            The mass of the cyclist in kilograms.
        height : float
            The height of the cyclist in meters.
        bike_mass : float
            The mass of the bike in kilograms.
        age : int
            The age of the cyclist in years.
        gender : Literal["f", "m"]
            The gender of the cyclist. Use "f" for female and "m" for male.
        recompute_altitude : bool, optional
            Whether to recompute the altitude profile of the activity. 
            Set to True if you do not trust the altitude data from
            your device. Default is True.
        """
        activity_filepath = list(self.files.keys())[index-1]

        return Activity(
            fitparse.FitFile(activity_filepath),
            mass=mass,
            height=height,
            bike_mass=bike_mass,
            age=age,
            gender=gender
        )
    

    # --------------- #
    # !-- Readers --! #
    # --------------- #

    @staticmethod
    def _activity_metadata_from_file(filepath: str) -> dict:
        """
        Extracts metadata from a Garmin activity file.

        Returns
        -------
        dict
            A dictionary containing start_time, total_distance, total_ascent, and sport.
            All distances are in meters.
        """

        # 1. Load the FIT file
        fit_file = fitparse.FitFile(filepath)

        # 2. Get "Session" message
        session_message = next(fit_file.get_messages("session"))

        # 3. Extract relevant metadata
        metadata = {
            "start_time": session_message.get("start_time").value,
            "total_distance": session_message.get("total_distance").value,
            "total_ascent": session_message.get("total_ascent").value,
            "sport": session_message.get("sport").value,
            "start_position_lat": session_message.get("start_position_lat").value / 11930465,
            "start_position_long": session_message.get("start_position_long").value / 11930465, # in degrees
        }

        # 4. Extract enhanced_avg_speed if available, else extract avg_speed
        enhanced_avg_speed = session_message.get("enhanced_avg_speed")
        if enhanced_avg_speed is not None:
            metadata["avg_speed"] = enhanced_avg_speed.value * 3.6
        else:
            metadata["avg_speed"] = session_message.get("avg_speed").value * 3.6

        lon, lat = metadata["start_position_long"], metadata["start_position_lat"]
        if str((np.round(lon, 3), np.round(lat, 3))) in ActivitySet.city_cache:
            metadata["city"] = ActivitySet.city_cache[str((np.round(lon, 3), np.round(lat, 3)))]
        return metadata
    
    @staticmethod
    def _find_city(lon, lat):
        """
        Finds the city name based on the provided
        longitude and latitude using the Nominatim
        geocoding service.
        """
        lon, lat = np.round(lon, 3), np.round(lat, 3)
        if str((lon, lat)) in ActivitySet.city_cache:
            return ActivitySet.city_cache[str((lon, lat))]
        geolocator = geopy.Nominatim(user_agent="garmin_analytics")
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location and "city" in location.raw["address"]:
            city = location.raw["address"]["city"]
        elif location and "town" in location.raw["address"]:
            city =location.raw["address"]["town"]
        elif location and "village" in location.raw["address"]:
            city = location.raw["address"]["village"]
        else:
            city = "unknown"
        ActivitySet.city_cache[str((lon, lat))] = city
        return city

    
    @staticmethod
    def _user_metadata_from_file(filepath: str) -> dict:
        """
        Extracts user metadata from a Garmin activity file.

        Returns
        -------
        dict
            A dictionary containing user_id, weight, height, gender.
            Weight is in kilograms and height is in meters.
        """

        # 1. Load the FIT file
        fit_file = fitparse.FitFile(filepath)

        # 2. Get "UserProfile" message
        user_profile_message = next(fit_file.get_messages("user_profile"))

        # 3. Extract relevant metadata
        metadata = {
            "weight": user_profile_message.get("weight").value,
            "height": user_profile_message.get("height").value,
            "gender": user_profile_message.get("gender").value[0],
        }
        
        return metadata