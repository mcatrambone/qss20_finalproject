## Load in data: 

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
 
PATH = "/Users/mattcatrambone/Desktop/qss20_proj/data_2024_2025"

geo = pd.read_csv(f"{PATH}/AHRF2025geo.csv", sep=",", encoding="latin1", low_memory=False)
hp  = pd.read_csv(f"{PATH}/AHRF2025hp.csv",  sep=",", encoding="latin1", low_memory=False)
pop = pd.read_csv(f"{PATH}/AHRF2025pop.csv",  sep=",", encoding="latin1", low_memory=False)
