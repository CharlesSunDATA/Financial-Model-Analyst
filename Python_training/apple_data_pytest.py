import pandas as pd
import matplotlib.pyplot as plt

# Load data from CSV file
df = pd.read_csv('apple_data_test.csv')

# Plot the data
fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot revenue
ax1.set_xlabel('Year')
ax1.set_ylabel('Revenue (in billions)', color='tab:blue')
ax1.plot(df['Year'], df['Revenue (in billions)'], color='tab:blue', marker='o', label='Revenue')
ax1.tick_params(axis='y', labelcolor='tab:blue')

# Create a second y-axis to plot employees
ax2 = ax1.twinx()
ax2.set_ylabel('Employees (in thousands)', color='tab:green')
ax2.plot(df['Year'], df['Employees (in thousands)'], color='tab:green', marker='x', label='Employees')
ax2.tick_params(axis='y', labelcolor='tab:green')

# Add title and show plot
plt.title('Apple Revenue and Employees Over the Last 5 Years')
fig.tight_layout()
plt.show()
