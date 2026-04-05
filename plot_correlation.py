import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# 1. Load dataset
data = pd.read_csv("flows_preprocessed_with_prediction.csv")

# 2. Remove non-numeric columns
X = data.drop(columns=['label', 'src_ip', 'dst_ip'], errors='ignore')
X = X.apply(pd.to_numeric, errors='coerce')

# 3. Clean Data (This fixes the blank white lines)
# Drop columns that are completely NaN
X = X.dropna(axis=1, how='all')
# Fill remaining NaNs
X = X.fillna(0)
# Drop features with zero variance (constants) to prevent NaN correlations
X = X.loc[:, X.nunique() > 1] 

# 4. Calculate Correlation matrix
corr = X.corr()
corr = corr.loc[corr.abs().sum().sort_values(ascending=False).index]

# 5. Generate a mask for the upper triangle (removes duplicate visual clutter)
mask = np.triu(np.ones_like(corr, dtype=bool))

# 6. Set up the matplotlib figure
plt.figure(figsize=(14, 12))

# 7. Plot heatmap
sns.heatmap(corr, 
            mask=mask, 
            cmap="coolwarm", # 'coolwarm' or 'RdBu_r' look a bit more modern, but 'RdYlGn' works too
            vmin=-1, vmax=1, # Strictly binds the color scale from -1 to 1
            center=0,        # Sets the middle color to 0
            square=True,     # Makes each cell a perfect square
            linewidths=0.5,  # Adds a thin gridline between cells
            cbar_kws={"shrink": .8}) # Shrinks the colorbar slightly to match the plot height

# 8. Improve text readability
plt.title("Correlation Matrix of Feature Set", fontsize=18, pad=20)
plt.xticks(rotation=45, ha='right', fontsize=10) # Angles labels so they don't overlap
plt.yticks(rotation=0, fontsize=10)
plt.tight_layout() # Prevents the outer labels from getting chopped off

# Show plot
plt.show()