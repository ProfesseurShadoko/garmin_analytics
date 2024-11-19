
from .activity import Activity
from .metrics import *
from .fancy_package import Message, Task, cstr

import datetime
import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import gaussian_kde
from scipy.optimize import curve_fit

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
plt.style.use('dark_background')



#############
### UTILS ###
#############

def smoothen_on_distance(activity:Activity, columns:list[str], distance_window:float=2000) -> pd.DataFrame:
    if isinstance(columns, str):
        columns = [columns]
    assert isinstance(columns, list), "columns must be a list of strings"
    
    data = activity.get_data(columns=['distance', *columns])
    dx = data['distance'].diff().median()
    window = int(distance_window / dx)
    
    for column in columns:
        data[column] = data[column].interpolate(method='linear')
        data[column] = savgol_filter(data[column], window, 3)
    return data



##################
### STATISTICS ###
##################

def display_activity_stats(activity:Activity):
    activity_stats = Activity.get_metrics(activity)
    
    Message("Activity stats:")
    with Message.tab():
        
        # total duration
        ""
        Message.print(
            "Moving time: " + cstr(
                datetime.timedelta(seconds=activity_stats['duration_s'])
            ).bold().cyan()
        )
        
        # total distance
        Message.print(
            "Distance: " + cstr(
                round(activity_stats['distance_km'], 1)
            ).bold().cyan() + " km"
        )
        
        # total ascent
        Message.print(
            "Total Ascent: " + cstr(
                round(activity_stats['elevation_gain_m'])
            ).bold().cyan() + " m"
        )
        
        Message.print(ignore_tabs=True)
        
        # average speed
        Message.print(
            "Average Speed: " + cstr(
                round(activity_stats['average_speed_kmh'], 1)
            ).bold().cyan() + " km/h"
        )
        
        # Max speed
        Message.print(
            "Maximal Speed: " + cstr(
                round(activity_stats['max_speed_kmh'], 1)
            ).bold().cyan() + " km/h"
        )
        
        # Slope Adjusted Average Speed
        Message.print(
            "Averaged speed adjusted to the slope: " + cstr(
                round(activity_stats['slope_adjusted_average_speed_kmh'], 1)
            ).bold().cyan() + " km/h"
        )

        
        Message.print(ignore_tabs=True)
        
        # Average power
        Message.print(
            "Mean Power: " + cstr(
                round(activity_stats['average_power_w'])
            ).bold().cyan() + " W"
        )
        
        # FTP
        Message.print(
            "Functionnal Treshold Power (FTP): " + cstr(
                round(activity_stats['ftp_wkg'], 2)
            ).bold().cyan() + " W/kg"
        )
        
        # PPO
        Message.print(
            "Peak Power Output (PPO): " + cstr(
                round(activity_stats['ppo_w'])
            ).bold().cyan() + " W"
        )
        
        Message.print(ignore_tabs=True)
        
        # Average Heart Rate
        Message.print(
            "Mean Heart Rate: " + cstr(
                round(activity_stats['average_heart_rate_bpm'])
            ).bold().cyan() + " bpm"
        )
        
        # VO2 max
        Message.print(
            "VO2 max: " + cstr(
                round(activity_stats['vo2max_mlkgmin'])
            ).bold().cyan() + " mL/kg/min"
        )
        
        # TSS
        Message.print(
            "Training Stress Score (TSS): " + cstr(
                round(activity_stats["normalized_training_stress_score"])
            ).bold().cyan()
        )
        
        # Calories and all
        Message.print(ignore_tabs=True)
        Message.print(
            "Calories: " + cstr(
                round(activity_stats['calories_kcal'])
            ).bold().cyan() + " kcal"
        )
        
        Message.print(
            "Efficiency: " + cstr(
                activity_stats['efficiency_%']/100, format_spec=".0%"
            ).bold().cyan()
        )
   
   

######################
### ADJUSTED SPEED ###
######################     
        

def plot_adj_speed(activity: Activity):
    plt.figure(figsize=(15, 5))
    grid = GridSpec(2, 5)
    plt.subplot(grid[:, :3])
    plt.suptitle("Comparison between speed\nand speed adjusted to slope")
    data_adj = smoothen_on_distance(activity, ['adj_speed', 'speed'], 2000)
    data = activity.get_data(columns=['distance', 'speed'])
    
    plt.scatter(data['distance'] / 1e3, data['speed']*3.6, label='Speed', color='gray', s=3, alpha=0.5, marker='x')

    plt.plot(data_adj['distance'] / 1e3, data_adj['speed']*3.6, label='Smooth speed', color='cyan')
    plt.plot(data_adj['distance'] / 1e3, data_adj['adj_speed']*3.6, label='Speed adjusted to slope', color='pink')
    
    plt.ylabel("Speed (km/h)")
    plt.xlabel("Distance (km)")
    plt.legend()
    
    # second plot show the two speed distributions
    data_adj = data_adj.dropna()
    
    v_grid = np.linspace(0, np.round(data_adj['speed'].max()*3.6, -1), 200)
    kde = gaussian_kde(data_adj['speed'].values * 3.6)
    kde_adj = gaussian_kde(data_adj['adj_speed'].values * 3.6)
    
    kde_values = kde(v_grid)
    kde_adj_values = kde_adj(v_grid)
    
    plt.subplot(grid[:, 3:])
    #plt.scatter(data_adj['speed']*3.6, data_adj['adj_speed']*3.6, s=3, alpha=0.5, color='cyan')
    plt.plot(v_grid, kde_values, label='Speed', color='cyan')
    plt.plot(v_grid, kde_adj_values, label='Adjusted speed', color='pink')
    plt.fill_between(v_grid, kde_values, color='cyan', alpha=0.5)
    plt.fill_between(v_grid, kde_adj_values, color='pink', alpha=0.5)
    plt.legend()
    plt.xlabel("Speed (km/h)")
    plt.yticks([])
    
    plt.show()
    
    
    

##################
### POWER - HR ###
##################

def plot_power_hr(activity: Activity):
    plt.figure(figsize=(15, 5), dpi=400)
    plt.suptitle("Power and Heart Rate")
    data_smooth = smoothen_on_distance(activity, ['watts', 'heart_rate'], 2000)
    data = activity.get_data(columns=['distance', 'watts', 'heart_rate'])
    
    grid = GridSpec(2, 4)
    ax = plt.subplot(grid[0, :2])
    ax.scatter(data['distance'][data['watts']>0] / 1e3, data['watts'][data['watts']>0], color='yellow', s=3, alpha=0.1, marker='x', zorder = 1)
    ax.plot(data_smooth['distance'] / 1e3, data_smooth['watts'], label='Power', color='yellow', zorder = 2)
    ax.set_ylabel("Power (W)")
    
    ax = plt.subplot(grid[1, :2])
    ax.scatter(data['distance'] / 1e3, data['heart_rate'], color='red', s=3, alpha=0.2, marker='x', zorder=1)
    ax.plot(data_smooth['distance'] / 1e3, data_smooth['heart_rate'], label='Heart Rate', color='red', zorder=2)
    ax.set_ylabel("Heart Rate (bpm)")
    ax.set_xlabel("Distance (km)")
    
    
    data = data[
        data['watts'] > 0
    ]
    
    ax = plt.subplot(grid[:, 2:])
    sm = ax.scatter(data['watts'], data['heart_rate'], c=data['distance'] / 1e3, s=3, alpha=0.5, cmap='viridis')
    
    # set y and x lim to 95 quantile
    ax.set_ylim(ax.get_ylim()[0], data['heart_rate'].quantile(0.95))
    ax.set_xlim(0, data['watts'].quantile(0.95))
    
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label('Distance (km)')
    
    ax.set_xlabel("Power (W)")
    ax.set_ylabel("Heart Rate (bpm)")
    plt.tight_layout()
    plt.show()
    
   


#####################
### SLOPE - POWER ###
#####################

def plot_slope_power(activity: Activity):
    plt.figure(figsize=(15, 5), dpi=400)
    plt.suptitle("Power and Slope")
    data_smooth = smoothen_on_distance(activity, ['watts', 'slope'], 2000)
    data = activity.get_data(columns=['distance', 'watts', 'slope'])
    
    data_smooth['slope'] *= 100
    data['slope'] *= 100
    
    grid = GridSpec(2, 4)
    ax = plt.subplot(grid[0, :2])
    ax.scatter(data['distance'][data['watts']>0] / 1e3, data['watts'][data['watts']>0], color='yellow', s=3, alpha=0.1, marker='x', zorder = 1)
    ax.plot(data_smooth['distance'] / 1e3, data_smooth['watts'], label='Power', color='yellow', zorder = 2)
    ax.set_ylabel("Power (W)")
    
    ax = plt.subplot(grid[1, :2])
    #ax.scatter(data['distance'] / 1e3, data['slope'], color='red', s=3, alpha=0.2, marker='x', zorder=1)
    data_smooth[data_smooth['slope']<0] = np.nan
    ax.plot(data_smooth['distance'] / 1e3, data_smooth['slope'], label='Pente', color='purple', zorder=2)
    ax.set_ylabel("Slope (%)")
    ax.set_xlabel("Distance (km)")
    
    
    data = data[
        (data['watts'] > 0) & (data['slope'] > 0)
    ]
    
    ax = plt.subplot(grid[:, 2:])
    sm = ax.scatter(data['watts'], data['slope'], c=data['distance'] / 1e3, s=3, alpha=0.5, cmap='viridis')
    
    # set y and x lim to 95 quantile
    ax.set_ylim(0, data['slope'].quantile(0.95))
    ax.set_xlim(0, data['watts'].quantile(0.95))
    
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label('Distance (km)')
    
    ax.set_xlabel("Power (W)")
    ax.set_ylabel("Slope (%)")
    plt.tight_layout()
    plt.show()






##########################
### POWER DISTRIBUTION ###
##########################

def plot_power_distribution(activity: Activity):
    
    grid = GridSpec(2, 4)
    # first lets compute power distribution
    data = activity.get_data(['distance', 'watts'])

    with Task("Computing Gaussian Kernel Density Estimation"):
        kde = gaussian_kde(data['watts'][data['watts']>0].values)
        x_grid = np.linspace(
            data['watts'][data['watts']>0].quantile(0.01),
            data['watts'][data['watts']>0].quantile(0.99),
            400
        )
        kde_values = kde(x_grid)
    
    
    with Task("Performing Gaussian Fit"):
    
        # try fitting gaussians
        def lognormal(x, A, mean, std):
            # return normalized gaussian function
            return A * (1 / (std * x)) * np.exp(-0.5 * ((np.log(x) - mean) / std) ** 2)
        
        
        initial_guess = [1, 100, 100]
        params, _ = curve_fit(lognormal, x_grid, kde_values, p0 = initial_guess)
        A1, m1, s1 = params
    
    # let's plot the result
    plt.figure(figsize=(15,5), dpi=400)
    plt.subplot(grid[0, :2])
    plt.plot(x_grid, kde_values, color='yellow')
    plt.fill_between(x_grid, kde_values, color='yellow', alpha=0.5)
    plt.title("Power distribution over the ride")
    plt.xlabel("Power (W)")
    plt.yticks([])
    
        
    
    plt.xlim(x_grid.min(), x_grid.max())
    
    # plot fitted gaussians too
    g1 = lognormal(x_grid, A1, m1, s1)
    plt.plot(x_grid, g1, linestyle='--', color='red', label='Lognormal fit', linewidth=2)
    plt.ylim(bottom=0)
    plt.legend()
    
    
    
    
    # let's plot at each distance the amount of power from each force
    data = activity.get_data(['distance', 'watts', 'drag', 'rolling_resistance', 'braking_power', 'delta_potential_energy', 'speed', 'delta_time_seconds'])
    data_smooth = smoothen_on_distance(activity, ['watts', 'drag', 'rolling_resistance', 'braking_power', 'delta_potential_energy', 'speed', 'delta_time_seconds'], 2000)
    
    drag_power = data_smooth['drag'] * data_smooth['speed']
    rolling_power = data_smooth['rolling_resistance'] * data_smooth['speed']
    braking_power = -data_smooth['braking_power']
    gravity_power = data_smooth['delta_potential_energy'] / data_smooth['delta_time_seconds']
    gravity_power[gravity_power<0] = 0
    
    plt.subplot(grid[1, :2])
    
    plt.fill_between(data['distance'] / 1e3, gravity_power, drag_power + gravity_power, color='lightblue', label='Drag')
    plt.fill_between(data['distance'] / 1e3, drag_power + gravity_power, gravity_power + drag_power + rolling_power, color='orange', label='Rolling Resistance')
    plt.fill_between(data['distance'] / 1e3, gravity_power + drag_power + rolling_power, gravity_power + drag_power + rolling_power + braking_power, color='red', label='Braking')
    plt.fill_between(data['distance'] / 1e3, 0, gravity_power, color='green', label='Gravity')
    plt.xlabel("Distance (km)")
    plt.ylabel("Power loss (W)")
    plt.ylim(top = (gravity_power + drag_power + rolling_power).quantile(0.99) * 1.1)
    plt.legend()  
    
    # one should get power = drag + resistance + braking (and no gravity since gravity conservative) but slight difference if elevation gain different from elevation loss
    
    
    
    
    
    # now we want to know where the power goes => altitude, breaking, drag.
    data = activity.get_data(['distance', 'delta_time_seconds', 'watts', 'delta_potential_energy', 'delta_kinetic_energy', 'drag', 'speed', 'braking_power', 'rolling_resistance'])
    
    leg_energy = (data['watts'] * data['delta_time_seconds']).sum()
    drag_energy = (data['drag'] * data['speed'] * data['delta_time_seconds']).abs().sum()
    rolling_energy = (data['rolling_resistance'] * data['speed'] * data['delta_time_seconds']).abs().sum()
    braking_energy = (data['braking_power'] * data['delta_time_seconds']).abs().sum()
    
    delta_potential_energy = smoothen_on_distance(activity, 'delta_potential_energy', 200)
    potential_energy = delta_potential_energy[
        delta_potential_energy > 0
    ]['delta_potential_energy'].sum()
    
    # cake plot of energies
    
    plt.subplot(grid[:, 2:])
    labels = ['Watts', 'Braking',  'Rolling Resistance', 'Drag', 'Gravity']
    sizes = [leg_energy, braking_energy,  rolling_energy, drag_energy, potential_energy]
    colors = ['yellow', 'red',  'orange', 'lightblue', 'lightgreen']
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, wedgeprops=dict(alpha=0.5))
    plt.axis('equal')
    plt.title("Energy repartition")
    
    
    
    plt.tight_layout()
    plt.show()
    
    
    
    

###################
### MAP & SLOPE ###
###################

import folium
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import colors
from IPython.display import display, HTML

def plot_map(activity: Activity):
        df = activity.get_data(columns=['lon', 'lat', 'slope', 'distance'])
        df = df.dropna()
        
        df = df.reset_index(drop=True)
        
        lat_center = df['lat'].mean()
        lon_center = df['lon'].mean()
        
        m = folium.Map(location=[df['lat'].iloc[0],df["lon"].iloc[1]],zoom_start=18,tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
        
        # add lines of the stage depending on slope
        cmap = LinearSegmentedColormap.from_list(
            "mycmap", [(0, "green"), (0.04, "yellow"), (0.08, "orange"), (0.12, "red"), (0.16, "brown"), (0.20, "black"), (1,"black")]
        )
        
        def get_rolling_averager(window):
            """
            Args:
                window (float): returns a function to compute the avg slope over <window> meters
            """
            def get_avg_slope(row):
                
                return df[
                    (df["distance"]>row["distance"]-window/2) & (df["distance"]<row["distance"]+window/2)
                ]["slope"].mean()
                
            return get_avg_slope
                
        df['slope'] = df.apply(get_rolling_averager(100),axis=1)
        
        df['color'] = df['slope'].apply(lambda x: colors.to_hex(cmap(abs(x))))
        
        
        for i in range(0, len(df)-1):
            folium.PolyLine([df.loc[i, ['lat', 'lon']].values, df.loc[i+1, ['lat', 'lon']].values], color=df.loc[i, 'color']).add_to(m)
        #folium.PolyLine(df[['lat', 'lon']].values).add_to(m)
        
        folium.Circle(
            radius=10,
            location=[df['lat'].iloc[0], df['lon'].iloc[0]],
            popup='START',
            color="purple",
            fill=True
        ).add_to(m)
        
        folium.Circle(
            radius=10,
            location=[df['lat'].iloc[-1], df['lon'].iloc[-1]],
            popup='END',
            color="blue",
            fill=True
        ).add_to(m)
        
        folium.Marker()
        
        display(HTML(f'<div style="width:50vw;margin:auto;{m._repr_html_()}</div>'))
        
        legend_html = """
<div style="width:100%; fontsize:14px; display:flex; align-items:center; flex-direction:column;">
    <div>
    <b>Average slope over 100m</b><br>
    <div style="background: green; width: 10px; height: 10px; display: inline-block;"></div> 0%-4%<br>
    <div style="background: yellow; width: 10px; height: 10px; display: inline-block;"></div> 4%-8%<br>
    <div style="background: orange; width: 10px; height: 10px; display: inline-block;"></div> 8%-12%<br>
    <div style="background: red; width: 10px; height: 10px; display: inline-block;"></div> 12%-16%<br>
    <div style="background: brown; width: 10px; height: 10px; display: inline-block;"></div> 16%-20%<br>
    <div style="background: black; width: 10px; height: 10px; display: inline-block;"></div> >20%
    </div>
</div>
"""
        display(HTML(legend_html))
