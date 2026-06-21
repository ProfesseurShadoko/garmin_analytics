
import pandas as pd



# ------------------------ #
# !-- FTP calulcations --! #
# ------------------------ #

def min_periods(df:pd.DataFrame, minutes:int=0, seconds:int=0) -> int:
    """
    Columns
    -------
        'delta_time_seconds': time delta between two consecutive points in seconds
    Returns
    -------
        int: 95% confidence upper bound of time delta. Used to define min_periods with rolling.
    """
    
    tau = df["delta_time_seconds"].mean() + df["delta_time_seconds"].std()*2
    return int((60*minutes + seconds) / tau)


def get_ftp(df:pd.DataFrame) -> float:
    """
    FTP = 95% of the maximal 20 minutes power.
    
    Columns
    -------
    'time': datetime
    'watts': float
    'delta_time_seconds': float (s)
    """
    df = df.copy(deep=True).set_index('time')
    return df['watts'].rolling(window='20min', min_periods=min_periods(df, minutes=20)).mean().max() * 0.95


def get_ppo(df:pd.DataFrame) -> float:
    """    
    Columns
    -------
        'time': datetime
        'watts': float
        'delta_time_seconds': float (s)
    """
    df = df.copy(deep=True).set_index('time')
    return df['watts'].rolling(window='150s', min_periods=min_periods(df, seconds=150)).mean().max()

def get_vo2max(df:pd.DataFrame, mass:float, gender:str) -> float:
    """
    Returns:
        VO_{2 max}: (mL/kg/min)
    
    Columns
    -------
        'time': datetime
        'watts': float (W)
        'delta_time_seconds': float (s)
    """
    assert gender in ["m", "f"], "Gender must be 'm' or 'f'."
    def vo2max_v2(ppo, mass, gender):
        if gender == "m":
            return (10.791 * ppo / mass) + 7
        else:
            return (9.820 * ppo / mass) + 7
        
    return vo2max_v2(ppo=get_ppo(df), mass=mass, gender=gender)


# ------------------------ #
# !-- Training Metrics --! #
# ------------------------ #


def get_normalized_power(df:pd.DataFrame) -> float:
    """
    Columns
    -------
        'watts': float
    """
    return (df["watts"]**4).mean()**(1/4)


def get_intensity_factor(df:pd.DataFrame) -> float:
    """
    Columns
    -------
        'time': datetime
        'watts': float
        'delta_time_seconds': float (s)
    """
    return get_normalized_power(df) / get_ftp(df)

def get_training_stress_score(df:pd.DataFrame, mass:float = None, absolute:bool = False) -> float:
    """
    Columns
    -------
        'cumulative_time_seconds': float (s)
        'watts': float (W)
        'delta_time_seconds': float (s)
    """
    if not absolute:
        return df["cumulative_time_seconds"].max() * get_normalized_power(df) * get_intensity_factor(df) / (get_ftp(df) * 3600) * 100
    else:
        assert mass is not None, "mass must be provided when absolute is True."
        return df["cumulative_time_seconds"].max() * get_normalized_power(df) * get_intensity_factor(df) * get_ftp(df) / 36 / (3.5*mass)**2


# ------------------ #
# !-- Watt Gains --! #
# ------------------ #

def get_speed_gain_per_watt(df:pd.DataFrame) -> float:
    """
    Columns
    -------
        'delta_watt_per_ms': float (W per m/s)
    
    Returns
    -------
        float: number of m/s gained per additional watt
    """
    mask = df["delta_watt_per_ms"] > 0
    return df.loc[mask, "delta_watt_per_ms"].median()

def get_watt_gain_per_kg(df:pd.DataFrame) -> float:
    """
    Columns
    -------
        'delta_watt_per_kg': float (W per kg)
    
    Returns
    -------
        float: number of W saved per kg lost
    """
    mask = df["delta_watt_per_kg"] > 0
    return df.loc[mask, "delta_watt_per_kg"].median()

def get_time_gain_per_watt(df:pd.DataFrame) -> float:
    """
    Columns
    -------
        'delta_watt_per_ms': float (W per m/s)
    
    Returns
    -------
        float: number of seconds gained per watt saved over 1 km
    """
    speed_gain_per_watt = get_speed_gain_per_watt(df)
    total_distance_m = df["distance"].iloc[-1]
    average_speed_m_s = df["speed"].median()
    
    return total_distance_m / (average_speed_m_s ** 2) * speed_gain_per_watt



# ----------------- #
# !-- Nutrition --! #
# ----------------- #

def get_calories(df:pd.DataFrame, mass:float, age:int) -> float:
    """
    Columns
    -------
        'watts': float (W)
        'delta_time_seconds': float (s)
        'heart_rate': float (bpm)
    
    Returns
    -------
        float: Calories burned (kcal)
    """
    return ((age * 0.2017 - 0.09036 * mass + df['heart_rate'] * 0.6309 - 55.0969)*(df['delta_time_seconds']/60)).sum()/4.184 # kJ to kcal


def get_equivalent_pasta_grams(df:pd.DataFrame, mass:float, age:int) -> float:
    """
    Calls get_calories to get calories and convert to grams of pasta.
    
    Columns
    -------
        'watts': float (W)
        'delta_time_seconds': float (s)
        'heart_rate': float (bpm)
    
    Returns
    -------
        float: Equivalent grams of pasta (assuming 3.5 kcal per gram) before cooking.
    """
    return get_calories(df, mass, age) / 3.5

def get_equivalent_co2(df:pd.DataFrame) -> float:
    """
    Columns
    -------
        'distance': float (m)
    
    Returns
    -------
        float: Equivalent CO2 saved in kg.
    """
    d_km = df["distance"].iloc[-1] / 1000
    # co2_bike = 21e-3 * d_km # 21g of CO2 per km by bike (comes from manufacturing, otherwise negligeable, so let's neglect it)
    co2_car = 106e-3 * d_km # 106g of CO2 per km by car
    
    # FYI: regional plane is aroung 200g CO2 per km, long distance plane around 80g CO2 per km, train around 3g in France, 60g in Europe 
    # because of electricity mix.
    return co2_car

def get_efficiency(df:pd.DataFrame, mass:float, age:float) -> float:
    """
    Columns
    -------
        'watts': float (W)
        'delta_time_seconds': float (s)
        'heart_rate': float (bpm)
    
    Returns
    -------
        float: Efficiency in percentage (should be between 0 and 1)
    """
    watts_in_kcal = (df['watts'] * df['delta_time_seconds']).sum() / 4184 # J to kcal
    kcal_from_heart_rate = get_calories(df, mass, age)
    return watts_in_kcal / kcal_from_heart_rate
