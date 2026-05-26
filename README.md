# QSS 20 Final Project - Matt Catrambone
Public repository for my final project in QSS20 regarding rural health disparities. 

Research question: Does spatiotemporal access to care predict county-level mortality better than traditional provider-to-population ratios in rural U.S. counties?

This project compares drive-time-based accessibility measures against conventional supply metrics (PCP-to-population ratios, HPSA designations) as predictors of all-cause and disease-specific mortality, stratified by rurality. Data are county-level from the AHRF 2024–2025 release, supplemented with FCC broadband data and OpenStreetMap road network data.

**Data source: **

AHRF 2024-2025 (Area Health Resources File, Bureau of Health Workforce, HRSA (U.S. DHHS)). County-level combination of datasets that draws from AMA physician data, Census Bureau population estimates, CMS, and ERS rural classification systems. Full variable documentation is located in data/AHRF_2024-2025_Technical_Documentation.xlsx.

**Data files: **

data/AHRF 2024-2025 Technical Documentation.xlsx is the documentation guide provided by AHRF that can be used to familiarize with the dataset. 

data/AHRF2025geo.csv contains geographic and rural classification variables, such as county codes, rural-urban continuum codes (RUCA), and urban influence codes. 

data/AHRF2025hp.csv contains county-level health professional variables, such as the number of non-federal primary care physicians, total number of specialists, specialty-level counts by speciality, and primary care designations. 

data/AHRF2025pop.csv contains population statistics by county as well as information on mortality and socioeconomic status variables. 

**Scripts: **

00_pullandmerge: Loads the three AHRF 2024–2025 sub-files and merge them into a single flat county-level dataframe.

01_clean: Selects analytic variables, enforces correct dtypes, constructs derived measures, filters implausible values, and produces the clean analytic dataset.

02_plots: Produces the two starter visualizations described in Milestone 1. 
