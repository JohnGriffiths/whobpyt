.. _datasets:

Datasets Overview
#################

Datasets and corresponding data fetcher functions are provided for all the whobpyt examples. Several of these are hosted and viewable on the `<whobpyt-data open science framework (OSF) respository https://osf.io/u7kgw/overview>`_. 

The data fetcher structure can be seen in the `<Momi et al. 2023 example: >_ https://griffithslab.github.io/whobpyt/auto_examples/eg__momi2023.html`.

.. code-block:: python  
from whobpyt.datasets.fetchers import fetch_egmomi2023  
files_dir = fetch_egmomi2023()   
sc_file = files_dir + '/Schaefer2018_200Parcels_7Networks_count.csv'  
high_file =files_dir + '/only_high_trial.mat'  
dist_file = files_dir + '/Schaefer2018_200Parcels_7Networks_distance.csv'  
file_eeg = files_dir + '/label_ts_corrected'  
file_leadfield = files_dir + '/leadfield'  
file_eeg = files_dir + '/real_EEG'  
eeg = np.load(file_eeg, allow_pickle=True)  


