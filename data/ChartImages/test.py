import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors

# Using weighted luminance formula
def rgb_to_luminance(rgb_array):
    # Normalize RGB to 0-1 range
    rgb_normalized = rgb_array / 255.0

    # Weights based on human perception of brightness
    weights = np.array([0.299, 0.587, 0.114])

    # Calculate luminance
    return np.sum(rgb_normalized * weights, axis=1)

# Sample data
rgb_colors = np.array([
    [255, 0, 0],    # Red
    [255, 127, 0],  # Orange
    [255, 255, 0],  # Yellow
    [0, 255, 0],    # Green
    [0, 0, 255],    # Blue
    [75, 0, 130],   # Indigo
    [148, 0, 211],   # Violet
    [0,0,0],
    [255,255,255],
    [100,100,100]
])

# Normalize colors
normalized_colors = rgb_colors / 255.0

# Create x values (can be any meaningful metric for your data)
x = rgb_to_luminance(rgb_colors)

# Plot
plt.figure(figsize=(10, 6))
for i in range(len(x)):
    plt.scatter(x[i], 0, color=normalized_colors[i], s=100)

plt.yticks([])  # Hide y-axis
plt.title('RGB Color Spectrum')
plt.show()