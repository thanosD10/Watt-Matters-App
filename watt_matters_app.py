"""
Watt Matters App
"""

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style

import tkinter as tk
from tkinter import *

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

import datetime
from datetime import date
import time

import sqlite3
import pandas as pd
import numpy as np

#Color Values Reference
WHITE = "#ffffff"
GOLD = "#f8cb05"
DARK_BLUE = "#002588"
LIGHT_BLUE = "#093aff"
VERY_LIGHT_BLUE = "#cdd7ff"
DARK_GREY = "#b7b7b7"
LIGHT_GREY = "#e3e3e3"

# Matplotlib style
style.use("ggplot")

# Take environment variables from .env.
load_dotenv()


class WattMattersApp(tk.Tk):

    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        # App Geometry and Components
        self.geometry("600x1000+600+20")
        self.title("Watt Matters")
        photo = PhotoImage(file = "Image_Icons/watt-matters-logo.png")
        self.iconphoto(False, photo)
        self.resizable(False, False)
        self.configure(background=WHITE)

        # Create Container that every time contains the Page that is on top 
        container = tk.Frame(self, background=WHITE)
        container.configure(background=DARK_BLUE)
        container.pack(side=TOP, fill=BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Rotate between 4 pages(Energy, History, Insights, Profile)
        self.frames = {}

        for F in (EnergyPage, HistoryPage, InsightsPage, ProfilePage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # On start show Energy Page
        self.show_frame(EnergyPage)

    # Function that brings selected Page on top
    def show_frame(self, cont):

        frame = self.frames[cont]
        frame.tkraise()


# InfluxDB config
BUCKET = os.getenv('INFLUXDB_BUCKET')
client = InfluxDBClient(url=os.getenv('INFLUXDB_LOCALHOST_URL'),
                token=os.getenv('INFLUXDB_TOKEN'), org=os.getenv('INFLUXDB_ORG'))
write_api = client.write_api()

# Function that is querying the InfluxDB Time Series Database obtaining latest stored value
def query_latest_value_influxDB():
    # Query script - get last value
    query_api = client.query_api()
    query = 'from(bucket: "electricity")\
        |> range(start:1, stop: now())\
        |> filter(fn: (r) =>\
            r._measurement == "electricity"\
        )\
        |> last()'

    # Query InfluxDB database
    result = query_api.query(org=os.getenv('INFLUXDB_ORG'), query=query)
    value = []
    time = []
    # Store query results
    for table in result:
        for record in table.records:
            value.append((record.get_value()))
            time.append((record.get_time()))

    return value, time

# Read from file and store in Global variable to keep track of total watt usage
with open("total-watt.csv", "r") as file:
    last_line = file.readlines()[-1]
    currentline = last_line.split(",")
    total_watt = int(currentline[1])
    running_hours = float(currentline[2])

# Create figure for plotting
f = Figure(figsize=(5,5), dpi=100)
f.set_facecolor(LIGHT_GREY)
a = f.add_subplot(111)
xs = []
ys = []

# This function is called periodically(every 1 sec) from FuncAnimation
def animate(i, xs, ys):

    # Add x and y to lists
    value, time = query_latest_value_influxDB()
    xs.append(time[0])
    ys.append(value[0])

    # Keep track of total watt consumed
    global total_watt
    total_watt = total_watt + value[0]
    global running_hours
    running_hours = running_hours + 0.000278

    # Limit x and y lists to 3600 items (Keep metrics for last 3600 secs = 1 hour)
    xs = xs[-3600:]
    ys = ys[-3600:]

    # Draw x and y lists
    a.clear()
    a.plot(xs, ys, DARK_BLUE)
    a.set_facecolor(LIGHT_GREY)
    a.fill_between(xs, 0, ys, color=LIGHT_BLUE, alpha=0.5)

    # Rotate x-axis labels
    for tick in a.get_xticklabels():
        tick.set_rotation(45)

    # Format plot
    today = date.today().strftime("%d %B %Y")
    a.set_title('Live Energy Usage Diagram\n' + today)
    a.set_ylabel('Watt')
    a.set_xlabel('Time (sec)')

# Electricity usage table
def draw_usage_table(self):
    global text_watt
    global text_price

    # Watt Value
    frame_usage_watt = Frame(self, height=100, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
    frame_usage_watt.place(x=50, y=770)

    # kWh = ( (wattsPerSec ÷ 3600) × hrs) ÷ 1,000
    kWh = round(((total_watt / 3600) * running_hours) / 1000, 3)

    # StringVar variable
    text_watt = StringVar()
    # Give Text Value to StringVar Variable
    text_watt.set(str(kWh) + " kWh")

    label_usage_watt=tk.Label(frame_usage_watt, textvariable=text_watt, font='Helvetica 25 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
    frame_usage_watt.pack_propagate(False) 
    label_usage_watt.place(relx=0.5, rely=0.5, anchor=CENTER)

    # Watt Price in euro
    frame_usage_money = Frame(self, height=100, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
    frame_usage_money.place(x=300, y=770)

    # price in Greece: 1kWh = 0.12€
    price = round(kWh * 0.12, 3)

    # StringVar variable
    text_price = StringVar()
    # Give Text Value to StringVar Variable
    text_price.set(str(price) +  " €")

    label_usage_money=tk.Label(frame_usage_money, textvariable=text_price, font='Helvetica 25 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
    frame_usage_money.pack_propagate(False) 
    label_usage_money.place(relx=0.5, rely=0.5, anchor=CENTER)

# Refresh electricity usage table every 20 secs
def usageTableRefresher():

    # kWh = ( (wattsPerSec ÷ 3600) × hrs) ÷ 1,000
    kWh = round(((total_watt / 3600) * running_hours) / 1000, 3)
    text_watt.set(str(kWh) + " kWh")

    price = round(kWh * 0.12, 3)
    text_price.set(str(price) +  " €")

    app.after(20000, usageTableRefresher) # every 20 seconds...


class EnergyPage(tk.Frame):

    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent, background=WHITE)

        # Add Top Logo Frame
        frame_top_image = tk.Frame(self, height=123, width=600, borderwidth=2, bg=DARK_BLUE, relief=FLAT)
        frame_top_image.pack(side=TOP, fill="x")
        frame_top_image.picture = PhotoImage(file="Image_Icons/watt-matters-logo-full.png")
        frame_top_image.label = Label(frame_top_image, image=frame_top_image.picture, borderwidth=0)
        frame_top_image.label.pack()

        # Add Live Energy Consumption Tracking Graph
        frame_graph = Frame(self, height=550, width=600, bg=LIGHT_GREY, bd=1, relief=FLAT)
        frame_graph.place(x=0, y=150)
        frame_graph.pack_propagate(False)

        canvas = FigureCanvasTkAgg(f, frame_graph)
        canvas.draw()
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

        # Add Total Usage Today Table Frames
        frame_total_usage_today = Frame(self, height=40, width=500, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_total_usage_today.place(x=50, y=730)
        label_menu_energy = Label(frame_total_usage_today, text="Total Usage Today", font='Helvetica 18 bold', fg=DARK_BLUE, bg=DARK_GREY)
        frame_total_usage_today.pack_propagate(False) 
        label_menu_energy.place(relx=0.5, rely=0.5, anchor=CENTER)

        # Total Usage Table (Watt + Price)
        draw_usage_table(self)

        # Add Menu Buttons
        # Energy Button
        picture_energy = PhotoImage(file="Image_Icons/menu-energy.png")
        label_energy = Label(image=picture_energy)
        label_energy.image = picture_energy
        button_menu_energy = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Energy", fg=LIGHT_BLUE, font='Helvetica 16', image=label_energy.image, borderwidth=0, compound = TOP)
        button_menu_energy.place(x=0, y=900)

        # History Button
        picture_history = PhotoImage(file="Image_Icons/menu-history.png")
        label_history = Label(image=picture_history)
        label_history.image = picture_history
        button_menu_history = Button(self,height=90, width=125, bg=LIGHT_GREY, text="History", fg=LIGHT_BLUE, font='Helvetica 16', image=label_history.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(HistoryPage))
        button_menu_history.place(x=150, y=900)

        # Insights Button
        picture_insights = PhotoImage(file="Image_Icons/menu-insights.png")
        label_insights = Label(image=picture_insights)
        label_insights.image = picture_insights
        button_menu_insights = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Insights", fg=LIGHT_BLUE, font='Helvetica 16', image=label_insights.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(InsightsPage))
        button_menu_insights.place(x=300, y=900)

        # Profile Button
        picture_profile = PhotoImage(file="Image_Icons/menu-profile.png")
        label_profile = Label(image=picture_profile)
        label_profile.image = picture_profile
        button_menu_profile = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Profile", fg=LIGHT_BLUE, font='Helvetica 16', image=label_profile.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(ProfilePage))
        button_menu_profile.place(x=450, y=900)


# Plot history diagram
def history_diagram(self):
    # Load data file
    df = pd.read_csv('total-watt.csv')

    # Create/connect to a SQLite database
    conn = sqlite3.connect("watt_matters.db")

    # Create a cursor
    c = conn.cursor()

    # Load datafile to SQLire
    df.to_sql('total_usage', conn, if_exists='replace')


    # Query database
    query = "SELECT * FROM ( SELECT * FROM total_usage ORDER BY dates DESC LIMIT 11) ORDER BY dates ASC" # 11 = 10 last days + today
    date = []
    value = []
    # Execute query & store results
    for row in c.execute(query):
        date.append(row[1])
        value.append(round(((row[2] / 3600) * row[3]) / 1000, 3))

    # Remove today value
    date.pop();
    value.pop();

    # Commit command
    conn.commit()

    # Close connection
    conn.close()

    # Plot last 10 days History Graph
    fh = Figure(figsize=(5,5), dpi=100)
    fh.set_facecolor(LIGHT_GREY)
    a = fh.add_subplot(111)
    a.bar(date, value, color=LIGHT_BLUE)
    a.set_facecolor(LIGHT_GREY)

    # Format plot
    a.set_title('Energy Usage History\nlast 10 days')
    a.set_ylabel('kWh')
    a.set_xlabel('Date')

    # Rotate x-axis labels
    for tick in a.get_xticklabels():
        tick.set_rotation(50)

    # Frame to place history graph canvas
    frame_history_graph = Frame(self, height=720, width=600, bg=LIGHT_GREY, bd=1, relief=FLAT)
    frame_history_graph.place(x=0, y=150)
    frame_history_graph.pack_propagate(False)

    # Canvas to place history graph
    canvas = FigureCanvasTkAgg(fh, frame_history_graph)
    canvas.draw()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)


class HistoryPage(tk.Frame):

    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent, background=WHITE)

        # Add Top Logo Frame
        frame_top_image = tk.Frame(self, height=123, width=600, borderwidth=2, bg=DARK_BLUE, relief=FLAT)
        frame_top_image.pack(side=TOP, fill="x")
        frame_top_image.picture = PhotoImage(file="Image_Icons/watt-matters-logo-full.png")
        frame_top_image.label = Label(frame_top_image, image=frame_top_image.picture, borderwidth=0)
        frame_top_image.label.pack()

        # Add last 10 days History Graph
        history_diagram(self)

        # Add Menu Buttons
        # Energy Button
        picture_energy = PhotoImage(file="Image_Icons/menu-energy.png")
        label_energy = Label(image=picture_energy)
        label_energy.image = picture_energy
        button_menu_energy = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Energy", fg=LIGHT_BLUE, font='Helvetica 16', image=label_energy.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(EnergyPage))
        button_menu_energy.place(x=0, y=900)

        # History Button
        picture_history = PhotoImage(file="Image_Icons/menu-history.png")
        label_history = Label(image=picture_history)
        label_history.image = picture_history
        button_menu_history = Button(self,height=90, width=125, bg=LIGHT_GREY, text="History", fg=LIGHT_BLUE, font='Helvetica 16', image=label_history.image, borderwidth=0, compound = TOP)
        button_menu_history.place(x=150, y=900)

        # Insights Button
        picture_insights = PhotoImage(file="Image_Icons/menu-insights.png")
        label_insights = Label(image=picture_insights)
        label_insights.image = picture_insights
        button_menu_insights = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Insights", fg=LIGHT_BLUE, font='Helvetica 16', image=label_insights.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(InsightsPage))
        button_menu_insights.place(x=300, y=900)

        # Profile Button
        picture_profile = PhotoImage(file="Image_Icons/menu-profile.png")
        label_profile = Label(image=picture_profile)
        label_profile.image = picture_profile
        button_menu_profile = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Profile", fg=LIGHT_BLUE, font='Helvetica 16', image=label_profile.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(ProfilePage))
        button_menu_profile.place(x=450, y=900)


# Function that is querying the InfluxDB Time Series Database obtaining last 168 hours(week) measurements
def query_last_week_values_influxDB():
    # Query script - get last 168 hours(week) measurements
    query_api = client.query_api()
    query = 'from(bucket: "electricity")\
        |> range(start:-168h, stop: now())\
        |> filter(fn: (r) =>\
            r._measurement == "electricity"\
        )'

    # Query InfluxDB database
    result = query_api.query(org=os.getenv('INFLUXDB_ORG'), query=query)
    value = []
    time = []
    i = 0
    # Store query results
    for table in result:
        for record in table.records:
            value.append((record.get_value()))
            time.append((record.get_time()))
            i = i + 1

    # Convert query results into pandas dataframe
    measurement = np.vstack((value, time)).T
    dataframe=pd.DataFrame(measurement, columns=['value', 'time'])

    # Standart deviation
    std = dataframe.loc[:,"value"].std()
    # Highest consumption value
    max = dataframe.loc[:,"value"].max()
    # Lowest consumption value
    min = dataframe.loc[:,"value"].min()

    # Average energy consumption per morning, noon, afternoon and night
    # iterate through each row and select 'time' column respectively
    morning_sum = 0
    morning_count = 0
    noon_sum = 0
    noon_count = 0
    afternoon_sum = 0
    afternoon_count = 0
    night_sum = 0
    night_count = 0
    for ind in dataframe.index:
        # Get datetime
        date_time = dataframe['time'][ind]
        # Get only hour from datetime
        hour = str(date_time.time())[0:2]
        hour = int(hour)

        # [06:00 - 11:00] = Morning
        if hour >= 6 and hour < 12 :
            morning_sum = morning_sum + dataframe['value'][ind]
            morning_count = morning_count + 1

        # [12:00 - 17:00] = Noon
        elif hour >= 12 and hour < 18 :
            noon_sum = noon_sum + dataframe['value'][ind]
            noon_count = noon_count + 1

        # [18:00 - 23:00] = Afternoon
        elif hour >= 18 and hour <= 23:
            afternoon_sum = afternoon_sum + dataframe['value'][ind]
            afternoon_count = afternoon_count + 1

        # [00:00 - 05:00] = Night
        else:
            night_sum = night_sum + dataframe['value'][ind]
            night_count = night_count + 1

        # Calculate average consumption per morning, noon, afternoon and night
        if morning_count > 0 :
            morning_avg = morning_sum / morning_count
        else:
            morning_avg = 0

        if noon_count > 0 :
            noon_avg = noon_sum / noon_count
        else:
            noon_avg = 0

        if afternoon_count > 0 :
            afternoon_avg = afternoon_sum / afternoon_count
        else:
            afternoon_avg = 0

        if night_count > 0 :
            night_avg = night_sum / night_count
        else:
            night_avg = 0

    return std, max, min, morning_avg, noon_avg, afternoon_avg, night_avg

# Function that is querying the InfluxDB Time Series Database obtaining last 730 hours(month) measurements
def query_last_month_values_influxDB():
    # Query script - get last 730 hours(month measurements)
    query_api = client.query_api()
    query = 'from(bucket: "electricity")\
        |> range(start:-730h, stop: now())\
        |> filter(fn: (r) =>\
            r._measurement == "electricity"\
        )'

    # Query InfluxDB database
    result = query_api.query(org=os.getenv('INFLUXDB_ORG'), query=query)
    value = []
    time = []
    i = 0
    # Store query results
    for table in result:
        for record in table.records:
            value.append((record.get_value()))
            time.append((record.get_time()))
            i = i + 1

    # Convert query results into pandas dataframe
    measurement = np.vstack((value, time)).T
    dataframe=pd.DataFrame(measurement, columns=['value', 'time'])

    # Standart deviation
    std = dataframe.loc[:,"value"].std()
    # Highest consumption value
    max = dataframe.loc[:,"value"].max()
    # Lowest consumption value
    min = dataframe.loc[:,"value"].min()

    # Average energy consumption per morning, noon, afternoon and night
    # iterate through each row and select 'time' column respectively
    morning_sum = 0
    morning_count = 0
    noon_sum = 0
    noon_count = 0
    afternoon_sum = 0
    afternoon_count = 0
    night_sum = 0
    night_count = 0
    for ind in dataframe.index:
        # Get datetime
        date_time = dataframe['time'][ind]
        # Get only hour from datetime
        hour = str(date_time.time())[0:2]
        hour = int(hour)

        # [06:00 - 11:00] = Morning
        if hour >= 6 and hour < 12 :
            morning_sum = morning_sum + dataframe['value'][ind]
            morning_count = morning_count + 1

        # [12:00 - 17:00] = Noon
        elif hour >= 12 and hour < 18 :
            noon_sum = noon_sum + dataframe['value'][ind]
            noon_count = noon_count + 1

        # [18:00 - 23:00] = Afternoon
        elif hour >= 18 and hour <= 23:
            afternoon_sum = afternoon_sum + dataframe['value'][ind]
            afternoon_count = afternoon_count + 1

        # [00:00 - 05:00] = Night
        else:
            night_sum = night_sum + dataframe['value'][ind]
            night_count = night_count + 1

        # Calculate average consumption per morning, noon, afternoon and night
        if morning_count > 0 :
            morning_avg = morning_sum / morning_count
        else:
            morning_avg = 0

        if noon_count > 0 :
            noon_avg = noon_sum / noon_count
        else:
            noon_avg = 0

        if afternoon_count > 0 :
            afternoon_avg = afternoon_sum / afternoon_count
        else:
            afternoon_avg = 0

        if night_count > 0 :
            night_avg = night_sum / night_count
        else:
            night_avg = 0

    return std, max, min, morning_avg, noon_avg, afternoon_avg, night_avg

class InsightsPage(tk.Frame):
    
    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent, background=WHITE)
        global str_std_week
        global str_max_week
        global str_min_week
        global str_morning_avg_week
        global str_noon_avg_week
        global str_afternoon_avg_week
        global str_night_avg_week

        # Add Top Logo Frame
        frame_top_image = tk.Frame(self, height=123, width=600, borderwidth=2, bg=DARK_BLUE, relief=FLAT)
        frame_top_image.pack(side=TOP, fill="x")
        frame_top_image.picture = PhotoImage(file="Image_Icons/watt-matters-logo-full.png")
        frame_top_image.label = Label(frame_top_image, image=frame_top_image.picture, borderwidth=0)
        frame_top_image.label.pack()

        # Query InfluxDB database and get last week measurments
        std_week, max_week, min_week, morning_avg_week, noon_avg_week, afternoon_avg_week, night_avg_week = query_last_week_values_influxDB()

        # "Last Week" title
        frame_week = Frame(self, height=40, width=500, bg=DARK_BLUE, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week.place(x=50, y=140)
        label_week=tk.Label(frame_week, text="Last Week", font='Helvetica 20 bold', fg=GOLD, bg=DARK_BLUE)
        frame_week.pack_propagate(False) 
        label_week.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Week" std deviation Frames
        frame_week_std_deviation = Frame(self, height=50, width=250, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_std_deviation.place(x=50, y=180)
        label_week_std_deviation=tk.Label(frame_week_std_deviation, text="Standard Deviation", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_std_deviation.pack_propagate(False) 
        label_week_std_deviation.place(relx=0.5, rely=0.5, anchor=CENTER)

        frame_week_std_deviation_value = Frame(self, height=50, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_std_deviation_value.place(x=300, y=180)
        str_std_week = StringVar()
        str_std_week.set(str(round(std_week, 2)))
        label_week_std_deviation_value=tk.Label(frame_week_std_deviation_value, textvariable=str_std_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_std_deviation_value.pack_propagate(False) 
        label_week_std_deviation_value.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Week" highest energy consumption value Frames
        frame_week_max = Frame(self, height=50, width=250, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_max.place(x=50, y=230)
        label_week_max=tk.Label(frame_week_max, text="Highest Value", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_max.pack_propagate(False) 
        label_week_max.place(relx=0.5, rely=0.5, anchor=CENTER)

        frame_week_max_value = Frame(self, height=50, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_max_value.place(x=300, y=230)
        str_max_week = StringVar()
        str_max_week.set(str(max_week))
        label_week_max_value=tk.Label(frame_week_max_value, textvariable=str_max_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_max_value.pack_propagate(False) 
        label_week_max_value.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Week" lowest energy consumption value Frames
        frame_week_min = Frame(self, height=50, width=250, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_min.place(x=50, y=280)
        label_week_min=tk.Label(frame_week_min, text="Lowest Value", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_min.pack_propagate(False) 
        label_week_min.place(relx=0.5, rely=0.5, anchor=CENTER)

        frame_week_min_value = Frame(self, height=50, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_min_value.place(x=300, y=280)
        str_min_week = StringVar()
        str_min_week.set(str(min_week))
        label_week_min_value=tk.Label(frame_week_min_value, textvariable=str_min_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_min_value.pack_propagate(False) 
        label_week_min_value.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Week" average consumption Frames
        frame_week_avg_title = Frame(self, height=50, width=500, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_title.place(x=50, y=330)
        label_week_avg_title=tk.Label(frame_week_avg_title, text="Average Consumption", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_avg_title.pack_propagate(False)
        label_week_avg_title.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Morning
        frame_week_avg_morning = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_morning.place(x=50, y=380)
        label_week_avg_morning=tk.Label(frame_week_avg_morning, text="Morning", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_avg_morning.pack_propagate(False) 
        label_week_avg_morning.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Noon
        frame_week_avg_noon = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_noon.place(x=175, y=380)
        label_week_avg_noon=tk.Label(frame_week_avg_noon, text="Noon", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_avg_noon.pack_propagate(False) 
        label_week_avg_noon.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Afternoon
        frame_week_avg_afternoon = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_afternoon.place(x=300, y=380)
        label_week_avg_afternoon=tk.Label(frame_week_avg_afternoon, text="Afternoon", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_avg_afternoon.pack_propagate(False) 
        label_week_avg_afternoon.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Night
        frame_week_avg_night_value = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_night_value.place(x=425, y=380)
        label_week_avg_night_value=tk.Label(frame_week_avg_night_value, text="Night", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_week_avg_night_value.pack_propagate(False) 
        label_week_avg_night_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Morning avg value 
        frame_week_avg_morning_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_morning_value.place(x=50, y=430)
        str_morning_avg_week = StringVar()
        str_morning_avg_week.set(str(round(morning_avg_week, 2)))
        label_week_avg_morning_value=tk.Label(frame_week_avg_morning_value, textvariable=str_morning_avg_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_avg_morning_value.pack_propagate(False) 
        label_week_avg_morning_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Noon avg value
        frame_week_avg_noon_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_noon_value.place(x=175, y=430)
        str_noon_avg_week = StringVar()
        str_noon_avg_week.set(str(round(noon_avg_week, 2)))
        label_week_avg_noon_value=tk.Label(frame_week_avg_noon_value, textvariable=str_noon_avg_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_avg_noon_value.pack_propagate(False) 
        label_week_avg_noon_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Afternoon avg value
        frame_week_avg_afternoon_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_afternoon_value.place(x=300, y=430)
        str_afternoon_avg_week = StringVar()
        str_afternoon_avg_week.set(str(round(afternoon_avg_week, 2)))
        label_week_avg_afternoon_value=tk.Label(frame_week_avg_afternoon_value, textvariable=str_afternoon_avg_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_avg_afternoon_value.pack_propagate(False) 
        label_week_avg_afternoon_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Night avg value
        frame_week_avg_night_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_week_avg_night_value.place(x=425, y=430)
        str_night_avg_week = StringVar()
        str_night_avg_week.set(str(round(night_avg_week, 2)))
        label_week_avg_night_value=tk.Label(frame_week_avg_night_value, textvariable=str_night_avg_week, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_week_avg_night_value.pack_propagate(False) 
        label_week_avg_night_value.place(relx=0.5, rely=0.5, anchor=CENTER)


        global str_std_month
        global str_max_month
        global str_min_month
        global str_morning_avg_month
        global str_noon_avg_month
        global str_afternoon_avg_month
        global str_night_avg_month

        # Query InfluxDB database and get last month measurments
        std_month, max_month, min_month, morning_avg_month, noon_avg_month, afternoon_avg_month, night_avg_month = query_last_month_values_influxDB()

        # "Last Month" title
        frame_last_month_title = Frame(self, height=40, width=500, bg=DARK_BLUE, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_last_month_title.place(x=50, y=510)
        label_last_month_title=tk.Label(frame_last_month_title, text="Last Month", font='Helvetica 20 bold', fg=GOLD, bg=DARK_BLUE)
        frame_last_month_title.pack_propagate(False) 
        label_last_month_title.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Month" std deviation Frames
        frame_month_std_deviation = Frame(self, height=50, width=250, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_std_deviation.place(x=50, y=550)
        label_month_std_deviation=tk.Label(frame_month_std_deviation, text="Standard Deviation", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_std_deviation.pack_propagate(False) 
        label_month_std_deviation.place(relx=0.5, rely=0.5, anchor=CENTER)

        frame_month_std_deviation_value = Frame(self, height=50, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_std_deviation_value.place(x=300, y=550)
        str_std_month = StringVar()
        str_std_month.set(str(round(std_month, 2)))
        label_month_std_deviation_value=tk.Label(frame_month_std_deviation_value, textvariable=str_std_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_std_deviation_value.pack_propagate(False) 
        label_month_std_deviation_value.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Month" highest energy consumption value Frames
        frame_month_max = Frame(self, height=50, width=250, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_max.place(x=50, y=600)
        label_month_max=tk.Label(frame_month_max, text="Highest Value", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_max.pack_propagate(False) 
        label_month_max.place(relx=0.5, rely=0.5, anchor=CENTER)

        frame_month_max_value = Frame(self, height=50, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_max_value.place(x=300, y=600)
        str_max_month = StringVar()
        str_max_month.set(str(max_month))
        label_month_max_value=tk.Label(frame_month_max_value, textvariable=str_max_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_max_value.pack_propagate(False) 
        label_month_max_value.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Month" lowest energy consumption value Frames
        frame_month_min = Frame(self, height=50, width=250, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_min.place(x=50, y=650)
        label_month_min=tk.Label(frame_month_min, text="Lowest Value", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_min.pack_propagate(False) 
        label_month_min.place(relx=0.5, rely=0.5, anchor=CENTER)

        frame_month_min_value = Frame(self, height=50, width=250, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_min_value.place(x=300, y=650)
        str_min_month = StringVar()
        str_min_month.set(str(min_month))
        label_month_min_value=tk.Label(frame_month_min_value, textvariable=str_min_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_min_value.pack_propagate(False) 
        label_month_min_value.place(relx=0.5, rely=0.5, anchor=CENTER)

        # "Last Month" average consumption Frames
        frame_month_avg_title = Frame(self, height=50, width=500, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_title.place(x=50, y=700)
        label_month_avg_title=tk.Label(frame_month_avg_title, text="Average Consumption", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_avg_title.pack_propagate(False)
        label_month_avg_title.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Morning
        frame_month_avg_morning = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_morning.place(x=50, y=750)
        label_month_avg_morning=tk.Label(frame_month_avg_morning, text="Morning", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_avg_morning.pack_propagate(False) 
        label_month_avg_morning.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Noon
        frame_month_avg_noon = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_noon.place(x=175, y=750)
        label_month_avg_noon=tk.Label(frame_month_avg_noon, text="Noon", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_avg_noon.pack_propagate(False) 
        label_month_avg_noon.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Afternoon
        frame_month_avg_afternoon = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_afternoon.place(x=300, y=750)
        label_month_avg_afternoon=tk.Label(frame_month_avg_afternoon, text="Afternoon", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_avg_afternoon.pack_propagate(False) 
        label_month_avg_afternoon.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Night
        frame_month_avg_night_value = Frame(self, height=50, width=125, bg=DARK_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_night_value.place(x=425, y=750)
        label_month_avg_night_value=tk.Label(frame_month_avg_night_value, text="Night", font='Helvetica 17', fg=DARK_BLUE, bg=DARK_GREY)
        frame_month_avg_night_value.pack_propagate(False) 
        label_month_avg_night_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Morning avg value 
        frame_month_avg_morning_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_morning_value.place(x=50, y=800)
        str_morning_avg_month = StringVar()
        str_morning_avg_month.set(str(round(morning_avg_month, 2)))
        label_month_avg_morning_value=tk.Label(frame_month_avg_morning_value, textvariable=str_morning_avg_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_avg_morning_value.pack_propagate(False) 
        label_month_avg_morning_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Noon avg value
        frame_month_avg_noon_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_noon_value.place(x=175, y=800)
        str_noon_avg_month = StringVar()
        str_noon_avg_month.set(str(round(noon_avg_month, 2)))
        label_month_avg_noon_value=tk.Label(frame_month_avg_noon_value, textvariable=str_noon_avg_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_avg_noon_value.pack_propagate(False) 
        label_month_avg_noon_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Afternoon avg value
        frame_month_avg_afternoon_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_afternoon_value.place(x=300, y=800)
        str_afternoon_avg_month = StringVar()
        str_afternoon_avg_month.set(str(round(afternoon_avg_month, 2)))
        label_month_avg_afternoon_value=tk.Label(frame_month_avg_afternoon_value, textvariable=str_afternoon_avg_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_avg_afternoon_value.pack_propagate(False) 
        label_month_avg_afternoon_value.place(relx=0.5, rely=0.5, anchor=CENTER)

            # Night avg value
        frame_month_avg_night_value = Frame(self, height=50, width=125, bg=LIGHT_GREY, bd=1, highlightbackground=WHITE, highlightthickness=2, relief=FLAT)
        frame_month_avg_night_value.place(x=425, y=800)
        str_night_avg_month = StringVar()
        str_night_avg_month.set(str(round(night_avg_month, 2)))
        label_month_avg_night_value=tk.Label(frame_month_avg_night_value, textvariable=str_night_avg_month, font='Helvetica 17 bold', fg=DARK_BLUE, bg=LIGHT_GREY)
        frame_month_avg_night_value.pack_propagate(False) 
        label_month_avg_night_value.place(relx=0.5, rely=0.5, anchor=CENTER)


        # Add Menu Buttons
        # Energy Button
        picture_energy = PhotoImage(file="Image_Icons/menu-energy.png")
        label_energy = Label(image=picture_energy)
        label_energy.image = picture_energy
        button_menu_energy = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Energy", fg=LIGHT_BLUE, font='Helvetica 16', image=label_energy.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(EnergyPage))
        button_menu_energy.place(x=0, y=900)

        # History Button
        picture_history = PhotoImage(file="Image_Icons/menu-history.png")
        label_history = Label(image=picture_history)
        label_history.image = picture_history
        button_menu_history = Button(self,height=90, width=125, bg=LIGHT_GREY, text="History", fg=LIGHT_BLUE, font='Helvetica 16', image=label_history.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(HistoryPage))
        button_menu_history.place(x=150, y=900)

        # Insights Button
        picture_insights = PhotoImage(file="Image_Icons/menu-insights.png")
        label_insights = Label(image=picture_insights)
        label_insights.image = picture_insights
        button_menu_insights = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Insights", fg=LIGHT_BLUE, font='Helvetica 16', image=label_insights.image, borderwidth=0, compound = TOP)
        button_menu_insights.place(x=300, y=900)

        # Profile Button
        picture_profile = PhotoImage(file="Image_Icons/menu-profile.png")
        label_profile = Label(image=picture_profile)
        label_profile.image = picture_profile
        button_menu_profile = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Profile", fg=LIGHT_BLUE, font='Helvetica 16', image=label_profile.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(ProfilePage))
        button_menu_profile.place(x=450, y=900)

# Refresh insights table every 20 secs
def insightsTableRefresher():

    # Update insights table week values
    std_week, max_week, min_week, morning_avg_week, noon_avg_week, afternoon_avg_week, night_avg_week = query_last_week_values_influxDB()

    str_std_week.set(str(round(std_week, 2)))
    str_max_week.set(str(max_week))
    str_min_week.set(str(min_week))
    str_morning_avg_week.set(str(round(morning_avg_week, 2)))
    str_noon_avg_week.set(str(round(noon_avg_week, 2)))
    str_afternoon_avg_week.set(str(round(afternoon_avg_week, 2)))
    str_night_avg_week.set(str(round(night_avg_week, 2)))

    # Update insights table month values
    std_month, max_month, min_month, morning_avg_month, noon_avg_month, afternoon_avg_month, night_avg_month = query_last_month_values_influxDB()
    
    str_std_month.set(str(round(std_month, 2)))
    str_max_month.set(str(max_month))
    str_min_month.set(str(min_month))
    str_morning_avg_month.set(str(round(morning_avg_month, 2)))
    str_noon_avg_month.set(str(round(noon_avg_month, 2)))
    str_afternoon_avg_month.set(str(round(afternoon_avg_month, 2)))
    str_night_avg_month.set(str(round(night_avg_month, 2)))

    app.after(20000, insightsTableRefresher) # every 20 seconds...


class ProfilePage(tk.Frame):
    
    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent, background=WHITE)

        # Add Top Logo Frame
        frame_top_image = tk.Frame(self, height=123, width=600, borderwidth=2, bg=DARK_BLUE, relief=FLAT)
        frame_top_image.pack(side=TOP, fill="x")
        frame_top_image.picture = PhotoImage(file="Image_Icons/watt-matters-logo-full.png")
        frame_top_image.label = Label(frame_top_image, image=frame_top_image.picture, borderwidth=0)
        frame_top_image.label.pack()

        label = tk.Label(self, bg=WHITE)
        label.pack()

        # Add profile Image
        frame_prof_image = tk.Frame(self, borderwidth=2, bg=WHITE, relief=FLAT)
        frame_prof_image.pack(side=TOP, fill="x")
        frame_prof_image.picture = PhotoImage(file="Image_Icons/prof.png")
        frame_prof_image.label = Label(frame_prof_image, image=frame_prof_image.picture, borderwidth=0)
        frame_prof_image.label.pack()

        # Add profile Info
        frame_prof_image = tk.Frame(self, height=123, width=600, borderwidth=2, bg=WHITE, relief=FLAT)
        frame_prof_image.pack(side=TOP, fill="x")
        frame_prof_image.picture = PhotoImage(file="Image_Icons/prof-info.png")
        frame_prof_image.label = Label(frame_prof_image, image=frame_prof_image.picture, borderwidth=0)
        frame_prof_image.label.pack()


        # Add Menu Buttons
        # Energy Button
        picture_energy = PhotoImage(file="Image_Icons/menu-energy.png")
        label_energy = Label(image=picture_energy)
        label_energy.image = picture_energy
        button_menu_energy = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Energy", fg=LIGHT_BLUE, font='Helvetica 16', image=label_energy.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(EnergyPage))
        button_menu_energy.place(x=0, y=900)

        # History Button
        picture_history = PhotoImage(file="Image_Icons/menu-history.png")
        label_history = Label(image=picture_history)
        label_history.image = picture_history
        button_menu_history = Button(self,height=90, width=125, bg=LIGHT_GREY, text="History", fg=LIGHT_BLUE, font='Helvetica 16', image=label_history.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(HistoryPage))
        button_menu_history.place(x=150, y=900)

        # Insights Button
        picture_insights = PhotoImage(file="Image_Icons/menu-insights.png")
        label_insights = Label(image=picture_insights)
        label_insights.image = picture_insights
        button_menu_insights = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Insights", fg=LIGHT_BLUE, font='Helvetica 16', image=label_insights.image, borderwidth=0, compound = TOP,
                                     command=lambda: controller.show_frame(InsightsPage))
        button_menu_insights.place(x=300, y=900)

        # Profile Button
        picture_profile = PhotoImage(file="Image_Icons/menu-profile.png")
        label_profile = Label(image=picture_profile)
        label_profile.image = picture_profile
        button_menu_profile = Button(self,height=90, width=125, bg=LIGHT_GREY, text="Profile", fg=LIGHT_BLUE, font='Helvetica 16', image=label_profile.image, borderwidth=0, compound = TOP)
        button_menu_profile.place(x=450, y=900)


app = WattMattersApp()
ani = animation.FuncAnimation(f, animate, fargs=(xs, ys), interval=1000) #1000 millisec = 1 sec
usageTableRefresher()
insightsTableRefresher()

app.mainloop()
