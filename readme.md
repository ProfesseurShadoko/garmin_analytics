# Garmin Analytics: An Amateur Cyclist's Toolbox

**Garmin Analytics** is a project born from a love of cycling and curiosity about the science behind performance metrics. Designed for amateur cyclists, this project explores the physics of cycling and provides an accessible way to analyze and visualize your rides without needing a power meter.

The core of this project is the [garmin_analytics.ipynb](garmin_analytics.ipynb) notebook, which automates:

- ~~ Connecting to Garmin Connect to retrieve your profile and activity data. ~~
- Computing estimated power output using drag estimation, elevation changes, and speed variations.
- Visualizing various metrics like slope-corrected speed, peak power output (PPO), functional threshold power (FTP), VO₂ max, calorie consumption, power efficiency, and more.
- Vizualization of performance during automatically identified climbs

The goal of this project is to:

- **Learn** and have fun with the physics of cycling.
- **Share insights** into how platforms like Garmin compute their metrics.
- **Track progression** over time to gain a deeper understanding of training.

## How to Use

Clone the repository and install the dependencies:

```bash
git clone https://github.com/ProfesseurShadoko/garmin_analytics.git
pip install -r garmin_analytics/requirements.txt
```

Then, you wil need to download the data of your ride(s) (from Strava, Garmin Connect, etc.). The expected filetype is `.fit`, which is the default pretty much everywhere. Put all the files insied any directory. You must however add the path to this directory to your environment variables, as it will be loaded in python through `os.environ["GARMIN"]` (even if your device isn't a Garmin device). Alternatively, you can set `os.environ["GARMIN"] = "path/to/the/folder"` prior to running your code (see the notebook [garmin_analytics.ipynb](garmin_analytics.ipynb)).

## Get Started

Open the [garmin_analytics.ipynb](garmin_analytics.ipynb) file to dive into the analysis. The notebook contains detailed explanations of the computations, equations, and visualizations, making it easy to follow along and adapt the analysis to your needs.

## If you do not use Garmin

Don't worry, everything should work just the same! Just download the `.fit` files from Strava or anywhere.
