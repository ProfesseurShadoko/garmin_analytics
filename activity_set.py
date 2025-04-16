
from .fancy_package import Task, cstr, Message
from .activity import Activity

import datetime
import pandas as pd
import datetime

import io
import zipfile
import fitparse
from fitparse import FitFile
import garth

from typing import Literal

import getpass




class ActivitySet:
    user_settings:str = "/userprofile-service/userprofile/user-settings"
    activity_list:str = "/activitylist-service/activities/search/activities"
    download_service:str = "/download-service/files/activity"
    cycling_activity_ids:list = [2]
    current_instance = None
    
    ######################
    ### STATIC METHODS ###
    ######################
        
    @staticmethod
    def destroy() -> None:
        """
        ActivitySet() always returns a copy of the current instance. If you want to connect a new user, you must destroy the current instance.
        """
        ActivitySet.current_instance = None
    
    @staticmethod
    def connect(email:str, password:str) -> None:
        garth.login(email, password)
    
    @staticmethod
    def get_user_settings() -> dict:
        return garth.connectapi(ActivitySet.user_settings)['userData']
    
    @staticmethod
    def get_mass() -> float:
        """
        Returns:
        --------
            float: mass in kg
        """
        return ActivitySet.get_user_settings()['weight'] / 1000
    
    @staticmethod
    def get_height() -> float:
        """
        Returns:
        --------
            float: height in meters
        """
        return ActivitySet.get_user_settings()['height'] / 100
    
    @staticmethod
    def get_gender() -> Literal['m','f']:
        """
        Returns:
        --------
            gender: Literal['m','f']
        """   
        return 'm' if ActivitySet.get_user_settings()['gender']=='MALE' else 'f'
    
    
    @staticmethod
    def get_bike_mass() -> float:
        """
        Returns:
        --------
            float: bike mass in kg
        """
        raise(NotImplementedError("Mass of the bike cannot be accessed through Garmin."))
    
    @staticmethod
    def get_age() -> int:
        """
        Returns:
        --------
            int: age
        """
        date_str = ActivitySet.get_user_settings()['birthDate']
        age = (datetime.datetime.now() - datetime.datetime.strptime(date_str, '%Y-%m-%d')).days / 365.25
        return int(age)
    
    @staticmethod
    def get_activities() -> pd.DataFrame:
        """
        Returns:
        --------
            pd.DataFrame: dataframe with activities
        
        Columns:
        --------
            id: int (unique garmin activity id)
            name: str
            date: datetime.date
            distance_km: float (km)
            duration: datetime.timedelta
            elevationGain: float (m)
            avgSpeed_kmh: float (km/h)
            maxSpeed_kmh: float (km/h)

        """
        df = pd.DataFrame(garth.connectapi(ActivitySet.activity_list))
        Message.print(f"Retrieved {len(df)} activities from Garmin API")
        # find bike activities
        df["activityTypeId"] = df["activityType"].apply(lambda x: x["typeId"])
        df = df[df["activityTypeId"].isin(ActivitySet.cycling_activity_ids)].copy(deep=True)
        Message.print(f"Identified {len(df)} cycling activities")
        df["date"] = pd.to_datetime(df["startTimeGMT"]).dt.date
        df["distance_km"] = df["distance"] / 1000
        df["duration"] = df["duration"].apply(lambda x: datetime.timedelta(seconds=x))
        df["elevationGain"] = df["elevationGain"]
        df["avgSpeed_kmh"] = df["averageSpeed"] * 3.6
        df["maxSpeed_kmh"] = df["maxSpeed"] * 3.6
        df["name"] = df["activityName"]
        df["id"] = df["activityId"]
        
        return df[
            ["id", "name", "date", "distance_km", "duration", "elevationGain", "avgSpeed_kmh", "maxSpeed_kmh"]
        ].copy(deep=True)
    
    @staticmethod
    def download_activity(activity_id:int) -> FitFile:
        """
        Agrs:
        -----
            activity_id: int (unique garmin activity id, not the id from ActivitySet!)
        
        Returns:
        --------
            Raw FitFile object.
        """
        with Task("Downloading activity", new_line=False):
            data_bytes = garth.download(f"{ActivitySet.download_service}/{activity_id}")
        
        with Task("Extracting FIT file", new_line=False):
            with zipfile.ZipFile(io.BytesIO(data_bytes)) as z:
                with z.open(f"{activity_id}_ACTIVITY.fit") as f:
                    fit_data = f.read()

        return FitFile(fit_data)
    
    
    def __init__(self, email:str=None, password:str=None, bike_mass:float = None) -> None:
        """
        Connects to Garmin API and loads activities. If email or password are not provided, the user must input them.
        """
        # check for cached instance
        if ActivitySet.current_instance is not None:
            Message("Cached instance found! Copying cached instance.", "?")
            self.activities = ActivitySet.current_instance.activities.copy(deep=True)
            self.mass = ActivitySet.current_instance.mass
            self.height = ActivitySet.current_instance.height
            self.bike_mass = ActivitySet.current_instance.bike_mass
            self.age = ActivitySet.current_instance.age
            self.gender = ActivitySet.current_instance.gender
            return
        
        # if no saved values, ask the user
        if email is None or password is None:
            Message("Please enter your email and password to connect to Garmin API:")
            email = getpass.getpass(" > Email: ")
            password = getpass.getpass(" > Password: ")
        elif password is None:
            Message("Please enter your password to connect to Garmin API:")
            password = getpass.getpass(" > Password: ")
        
        with Task("Connecting to Garmin API", new_line=False):
            ActivitySet.connect(email, password)
        
        with Task("Retrieveing activities and user settings:", new_line=True):
            
            with Task("Retrieveing mass, height and bike mass", new_line=True):
                # get the mass
                try:
                    self.mass = ActivitySet.get_mass()
                except Exception as e:
                    Message("Could not retrieve user mass.", "!")
                    with Message.tab():
                        Message.print(e)
                    self.mass = int(input(" >> Your mass in kg: ").strip())
                
                # get the height
                try:
                    self.height = ActivitySet.get_height()
                except Exception as e:
                    Message("Could not retrieve user height.", "!")
                    with Message.tab():
                        Message.print(e)
                    self.height = int(input(" >> Your height in meters: ").strip())
                
                # get the bike mass
                try:
                    if bike_mass is not None:
                        self.bike_mass = bike_mass
                    else:
                        self.bike_mass = ActivitySet.get_bike_mass()
                except Exception as e:
                    Message("Could not retrieve bike mass.", "!")
                    with Message.tab():
                        Message.print(e)
                    self.bike_mass = int(input(" >> Bike mass in kg: ").strip())
                
                # get age
                try:
                    self.age = ActivitySet.get_age()
                except Exception as e:
                    Message("Could not retrieve user age.", "!")
                    with Message.tab():
                        Message.print(e)
                    self.age = int(input(" >> Your age in years: ").strip())
                
                # get geder
                try:
                    self.gender = ActivitySet.get_gender()
                except Exception as e:
                    Message("Could not retrieve user gender.", "!")
                    with Message.tab():
                        Message.print(e)
                    self.gender = input(" >> Your gender (m/f): ").strip()
                    assert self.gender in ['m','f']
                    
            # get the activities
            with Task("Retrieving activities", new_line=True):               
                self.activities = ActivitySet.get_activities()
            
            with Task("Removing activities < 30 minutes", new_line=True):
                previous_n_activities = len(self.activities)
                self.activities = self.activities[self.activities["duration"] > datetime.timedelta(minutes=30)].copy(deep=True)
                Message.print(f"Removed {cstr(len(self.activities)):y} activities out of {previous_n_activities} cycling activities.", "?")
                self.activities.reset_index(drop=True, inplace=True)
                
        
        Message.print(ignore_tabs=True)   
        Message("Activities loaded! Here's a recap:")
        with Message.tab():
            Message.print(f"Height: {cstr(self.height, format_spec='.2f'):c} m")
            Message.print(f"Mass: {cstr(self.mass, format_spec='.1f'):c} kg")
            Message.print(f"Bike mass: {cstr(self.bike_mass, format_spec='.1f'):c} kg")
            Message.print(f"Age: {cstr(self.age):c} years")
            Message.print(f"Gender: {cstr(self.gender.upper()):c}")
            Message.print(ignore_tabs=True)
            Message.print(f"Number of activities: {cstr(len(self.activities)):c}")
            
        ActivitySet.current_instance = self
        Message("ActivitySet successfully instantiated and cached!", "#")
        
        
    def display(self):
        """
        Show all activities with an ID for each of them, so that the user can select one.
        """
        Message(f"Cycling activities ({cstr(len(self.activities)):c}):")
        with Message.tab():
            for i, act in self.activities.iterrows():
                Message.print(f"{cstr(i+1):m}: {act['name']} ({cstr(act['date']).magenta()}) <{cstr(cstr(act['distance_km'], '.0f') + ' km'):r}>")

    
    def get(self, activity_id:int, recompute_altitude:bool=True) -> Activity:
        """
        Args:
        -----
            activity_id: int (id of the activity from the list, not the unique Garmin id!)
            
        Returns:
        --------
            Activity: Activity object
        """
        activity = self.activities.loc[activity_id-1] # set index starts at one!
        Message("Selected actvity:")
        with Message.tab():
            Message.print(f"Name: {activity['name']}")
            Message.print(f"Date: {activity['date']}")
            Message.print(f"ID: {activity['id']}")
        Message.print(ignore_tabs=True)
        with Task("Loading activity", new_line=True):
            fitfile = ActivitySet.download_activity(activity["id"]) # set index starts at one!
        
        Message.print(ignore_tabs=True)
        return Activity(fitfile, mass=self.mass, height=self.height, bike_mass=self.bike_mass, age=self.age, gender=self.gender, recompute_altitude=recompute_altitude)
    
    def __len__(self):
        return len(self.activities)
    
    
    def __iter__(self):
        self._current_id = 0 # id from the set, not garmin # starts at one since first thing __next__ does is increment
        return self
    
    def __next__(self) -> 'Activity':
        self._current_id += 1
        
        if self._current_id > len(self.activities):
            raise StopIteration()
        
        try:
            with Message.mute():
                with Task.mute():
                    return self.get(self._current_id)
        except Exception as e:
            Message.print(ignore_tabs=True)
            Message(f"Could not load activity {self._current_id}. Skipping.", "!")
            Message(f"Error message: {e} ({e.__class__.__name__})", "!")
            Message.print(ignore_tabs=True)
            return self.__next__()
    
    
