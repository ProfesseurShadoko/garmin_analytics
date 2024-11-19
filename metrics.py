
import pandas as pd

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



def get_calories(df:pd.DataFrame, mass:float, age:int) -> float:
    """
    Columns
    -------
        'watts': float (W)
        'delta_time_seconds': float (s)
        'heart_rate': float (bpm)
    """
    return ((age * 0.2017 - 0.09036 * mass + df['heart_rate'] * 0.6309 - 55.0969)*(df['delta_time_seconds']/60)).sum()/4.184 # kJ to kcal

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
