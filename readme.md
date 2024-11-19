# Garmin Analytics: An Amateur Cyclist's Toolbox

**Garmin Analytics** is a project born from a love of cycling and curiosity about the science behind performance metrics. Designed for amateur cyclists, this project explores the physics of cycling and provides an accessible way to analyze and visualize your rides without needing a power meter.

The core of this project is the **`garmin_analytics.ipynb`** notebook, which automates:

- Connecting to Garmin Connect to retrieve your profile and activity data.
- Computing estimated power output using drag estimation, elevation changes, and speed variations.
- Visualizing various metrics like slope-corrected speed, peak power output (PPO), functional threshold power (FTP), VO₂ max, calorie consumption, power efficiency, and more.

The goal of this project is to:

- **Learn** and have fun with the physics of cycling.
- **Share insights** into how platforms like Garmin compute their metrics.
- **Track progression** over time to gain a deeper understanding of training.

## Features

- Automatically fetches Garmin data, including personal metrics and activity history.
- Computes missing power data using physical principles.
- Creates visually rich plots to analyze individual rides and training progression.
- Fully runnable on **Google Colab** for ease of use—no setup required!

## How to Use

Clone the repository and install the dependencies:

```bash
!git clone https://github.com/ProfesseurShadoko/garmin_analytics.git
!pip install -r garmin_analytics/requirements.txt
```


Alternatively, you can explore and run the notebook directly on [Google Colab](https://colab.research.google.com/drive/1HUpoJkPbcm-DYhw0lHtFHNQtCdfP05UL "Open Colab"). This option simplifies the installation process, especially for those unfamiliar with Python, although it may run slightly slower.

## Get Started

Open the **`garmin_analytics.ipynb`** file to dive into the analysis. The notebook contains detailed explanations of the computations, equations, and visualizations, making it easy to follow along and adapt the analysis to your needs.

Whether you're here to have fun with physics, track your performance, or learn how platforms like Garmin and Strava process cycling data, **Garmin Analytics** is your gateway to uncovering the science behind the ride.

## Note from the author

This is my first project aimed at being shared with other people, so I am not yet familiar with how GitHub works or the best practices for organizing and presenting such projects. If you encounter any issues or have suggestions for improvement, please feel free to reach out or open an issue. I’m eager to learn and make this project as accessible and helpful as possible. Thank you for checking it out! 😃
