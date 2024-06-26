import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import argparse
import os
import warnings
from fractions import Fraction
import pytz

# Suppress specific FutureWarnings from Seaborn, if desired
warnings.simplefilter(action='ignore', category=FutureWarning)

def mm_to_inches(mm):
    inches = mm / 25.4
    return round(inches * 8) / 8

def process_and_plot(csv_file):
    df = pd.read_csv(csv_file)
    
    if 'Timestamp (PST)' not in df.columns:
        raise KeyError("'Timestamp (PST)' column is not found in the CSV file.")
    
    # Convert Unix timestamps to datetime objects
    df['Timestamp (PST)'] = pd.to_datetime(df['Timestamp (PST)'], unit='ms')
    df['Measurement'] = df['Measurement'].apply(mm_to_inches)

    # Ensure there are no zero or negative values for logarithmic scale
    # df['Measurement'] = df['Measurement'].replace(0, 0.125)  # Replace 0 with a small number
    df.set_index('Timestamp (PST)', inplace=True)
    grouped = df.groupby(['Sensor Number', pd.Grouper(freq='5s')]).min()
    grouped = grouped.reset_index()

    plt.figure(figsize=(16, 9))
    plot = sns.lineplot(data=grouped, x='Timestamp (PST)', y='Measurement', hue='Sensor Number', palette='tab10')

    plt.title('Minimum Measurement per Sensor Every 5 Seconds')
    plt.xlabel('Timestamp PST')
    plt.ylabel('Measurement (inches)')
    plt.legend(title='Sensor Number')
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S', tz=pytz.timezone('America/Los_Angeles')))
    plt.gcf().autofmt_xdate()

    # Set y-axis to logarithmic scale and limit y-axis
    plt.yscale('log')
    # plt.ylim(bottom=0, top=24)
    plt.autoscale(enable=True, axis='y')

    # Add horizontal lines at 1, 2, and 3 inches and label them
    for y_value, color, label in [(2.5, 'r', '2.5 inchs'), (5, 'y', '5 inches'), (10, 'g', '10 inches')]:
        plt.axhline(y=y_value, color=color, linestyle='--')
        plt.text(grouped['Timestamp (PST)'].iloc[-1], y_value, f'  {label}', verticalalignment='center', color=color)

    # Annotate the minimum measurement of each 5-second interval
    min_per_interval = grouped.groupby('Timestamp (PST)')['Measurement'].idxmin()
    for idx in min_per_interval:
        row = grouped.loc[idx]
        intnum = int(row["Measurement"])
        fracnum = Fraction(row["Measurement"] - intnum)
        Labeltxt = str(intnum) + " " + str(fracnum) + " in"
        plt.text(row['Timestamp (PST)'], row['Measurement']-1, Labeltxt,
                 color=plot.get_lines()[row['Sensor Number'] ].get_color(), fontsize=9)

    base_filename = os.path.splitext(os.path.basename(csv_file))[0]
    output_filename = base_filename + '.png'
    plt.savefig(output_filename)

    closest_readings = df.groupby('Sensor Number')['Measurement'].min()
    
    # Reset index to access 'Timestamp (PST)' column
    df = df.reset_index()
    closest_times = df.loc[df['Measurement'].isin(closest_readings)].groupby('Sensor Number')['Timestamp (PST)'].first()

    return closest_readings, closest_times

def main():
    parser = argparse.ArgumentParser(description='Process a CSV file to plot sensor measurements.')
    parser.add_argument('filename', type=str, help='CSV file to process')
    args = parser.parse_args()

    closest_readings, closest_times = process_and_plot(args.filename)
    for sensor, reading in closest_readings.items():
        print(f"Sensor {sensor} - Closest Reading: {reading} inches at {closest_times[sensor]}")

if __name__ == "__main__":
    main()
