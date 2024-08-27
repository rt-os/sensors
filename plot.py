import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import argparse
import os
import warnings
from fractions import Fraction

right_side_sensors = [0, 1]
left_side_sensors = [2, 3]
 
calibration_map = {
    0: -1,  #MM of adjustment negivite brings it closer to the cart
    1: -1,  
    2: -1,
    3: -1,
}

# Suppress specific FutureWarnings from Seaborn, if desired
warnings.simplefilter(action='ignore', category=FutureWarning)

# Set Monokai theme using rcParams
plt.rcParams.update({
    'axes.facecolor': '#272822',
    'axes.edgecolor': '#F8F8F2',
    'axes.labelcolor': '#F8F8F2',
    'figure.facecolor': '#272822',
    'grid.color': '#3E3D32',
    'text.color': '#F8F8F2',
    'xtick.color': '#F8F8F2',
    'ytick.color': '#F8F8F2',
    'legend.facecolor': '#272822',
    'legend.edgecolor': '#F8F8F2',
    'lines.color': '#A6E22E',  # Line color
    'lines.linewidth': 1.5,
    'savefig.facecolor': '#272822',
    'savefig.edgecolor': '#272822',
})
def apply_calibration(measurement, sensor_id, calibration_map):
    """Apply the calibration based on the sensor ID."""
    calibration_value = calibration_map.get(sensor_id, 0)  # Default to 0 if no calibration value is found
    return measurement + calibration_value


def mm_to_inches(mm):
    inches = mm / 25.4
    return round(inches * 8) / 8

def determine_grouping_frequency(start_time, end_time):
    duration_seconds = (end_time - start_time).total_seconds()
    sensors = 1  # Adjust this if you have multiple sensors or want different behavior per sensor

    # Calculate the number of intervals we want, which is between 5 and 20
    desired_intervals = min(max(duration_seconds // 5, 5), 20)

    frequency_seconds = duration_seconds / desired_intervals

    if frequency_seconds < 1:
        return '1S'  # Minimum frequency is 1 second
    elif frequency_seconds < 60:
        return f'{int(frequency_seconds)}S'
    elif frequency_seconds < 3600:
        return f'{int(frequency_seconds // 60)}T'  # 'T' is the alias for minutes
    else:
        return f'{int(frequency_seconds // 3600)}H'  # 'H' is the alias for hours

def convert_frequency_to_words(frequency):
    if 'S' in frequency:
        return f"{frequency.replace('S', '')} seconds"
    elif 'T' in frequency:
        return f"{frequency.replace('T', '')} minutes"
    elif 'H' in frequency:
        return f"{frequency.replace('H', '')} hours"
    else:
        return frequency

def process_and_plot(csv_file):
    df = pd.read_csv(csv_file)
    
    if 'Timestamp (PST)' not in df.columns:
        raise KeyError("'Timestamp (PST)' column is not found in the CSV file.")
    
    # Check if the timestamp is a Unix timestamp or a date string
    if pd.api.types.is_numeric_dtype(df['Timestamp (PST)']):
        df['Timestamp (PST)'] = pd.to_datetime(df['Timestamp (PST)'], unit='ms')
    else:
        df['Timestamp (PST)'] = pd.to_datetime(df['Timestamp (PST)'])
    
    # Apply calibration and convert to inches
    df['Measurement'] = df.apply(lambda row: mm_to_inches(apply_calibration(row['Measurement'], row['Sensor Number'], calibration_map)), axis=1)

    start_time = df['Timestamp (PST)'].min()
    end_time = df['Timestamp (PST)'].max()

    # Determine dynamic grouping frequency
    grouping_frequency = determine_grouping_frequency(start_time, end_time)
    grouping_frequency_words = convert_frequency_to_words(grouping_frequency)

    df.set_index('Timestamp (PST)', inplace=True)
    grouped = df.groupby(['Sensor Number', pd.Grouper(freq=grouping_frequency)]).min()
    grouped = grouped.reset_index()

    plt.figure(figsize=(16, 9))
    plot = sns.lineplot(data=grouped, x='Timestamp (PST)', y='Measurement', hue='Sensor Number', palette='tab10')

    plt.title(f'Minimum Measurement per Sensor (Grouped every {grouping_frequency_words})')
    plt.xlabel('Timestamp')
    plt.ylabel('Measurement (inches)')
    plt.legend(title='Sensor Number')
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    plt.gcf().autofmt_xdate()

    # Set y-axis to logarithmic scale and enable auto-scaling
    plt.yscale('log')
    plt.autoscale(enable=True, axis='y')

    # Add horizontal lines at 2.5, 5, and 10 inches and label them
    for y_value, color, label in [(2.5, '#E6DB74', '2.5 inches'), (5, '#AE81FF', '5 inches'), (10, '#66D9EF', '10 inches')]:
        plt.axhline(y=y_value, color=color, linestyle='--')
        plt.text(grouped['Timestamp (PST)'].iloc[-1], y_value, f'  {label}', verticalalignment='center', color=color)

    # Annotate the minimum measurement of each interval
    min_per_interval = grouped.groupby('Timestamp (PST)')['Measurement'].idxmin()
    for idx in min_per_interval:
        row = grouped.loc[idx]
        intnum = int(row["Measurement"])
        fracnum = Fraction(row["Measurement"] - intnum)
        Labeltxt = str(intnum) + " " + str(fracnum) + " in"
        plt.text(row['Timestamp (PST)'], row['Measurement']-1, Labeltxt,
                 color=plot.get_lines()[row['Sensor Number']].get_color(), fontsize=9)

    base_filename = os.path.splitext(os.path.basename(csv_file))[0]
    output_dir = os.path.dirname(csv_file)
    output_filename = os.path.join(output_dir, base_filename + '.png')
    plt.savefig(output_filename)

    closest_readings = df.groupby('Sensor Number')['Measurement'].min()
    
    # Reset index to access 'Timestamp (PST)' column
    df = df.reset_index()
    closest_times = df.loc[df['Measurement'].isin(closest_readings)].groupby('Sensor Number')['Timestamp (PST)'].first()

    # Close the figure to free up memory
    plt.close()
    
    return closest_readings, closest_times

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                try:
                    closest_readings, closest_times = process_and_plot(file_path)
                                       
                    # Find the lowest reading on the right side
                    right_side_readings = closest_readings[right_side_sensors]
                    lowest_right_sensor = right_side_readings.idxmin()
                    lowest_right_reading = right_side_readings.min()
                    lowest_right_time = closest_times[lowest_right_sensor]
                    
                    # Find the lowest reading on the left side
                    left_side_readings = closest_readings[left_side_sensors]
                    lowest_left_sensor = left_side_readings.idxmin()
                    lowest_left_reading = left_side_readings.min()
                    lowest_left_time = closest_times[lowest_left_sensor]
                    
                    # Extract the part of the filename after the last underscore
                    short_filename = file_path.split('_')[-1]
                    
                    print(f"{short_filename} - Right Side Lowest: Sensor {lowest_right_sensor} - Reading: {lowest_right_reading} inches ")
                    print(f"{short_filename} - Left Side Lowest: Sensor {lowest_left_sensor} - Reading: {lowest_left_reading} inches ")
                    
                except Exception as e:
                    print(f"Failed to process {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Process a CSV file or directory of CSV files to plot sensor measurements.')
    parser.add_argument('path', type=str, help='CSV file or directory containing CSV files to process')
    args = parser.parse_args()

    if os.path.isfile(args.path) and args.path.endswith('.csv'):
        closest_readings, closest_times = process_and_plot(args.path)
        for sensor, reading in closest_readings.items():
            print(f"Sensor {sensor} - Closest Reading: {reading} inches at {closest_times[sensor]}")
    elif os.path.isdir(args.path):
        process_directory(args.path)
    else:
        print(f"Invalid input: {args.path}. Please provide a valid CSV file or directory.")

if __name__ == "__main__":
    main()
