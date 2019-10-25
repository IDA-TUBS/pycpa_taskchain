# Welcome

This is an extension for [pyCPA](https://bitbucket.org/pycpa/pycpa).

# Installation and Usage

First, make sure you have [pyCPA](https://bitbucket.org/pycpa/pycpa) installed.

Second, you must either install this extension via `python setup.py install` or set you `PYTHONPATH` correctly (for experts).

Please refer to the scripts in the `examples` folder for usage examples.

# Publications and Benchmarks

The following publications have used and modified the analysis implemented here:

* \[EMSOFT17\]: J. Schlatow and R. Ernst, "Response-Time Analysis for Task Chains with Complex Precedence and Blocking Relations" in International Conference on Embedded Software, 2017
* \[RTAS16\]: J. Schlatow and R. Ernst, "Response-Time Analysis for Task Chains in Communicating Threads" in Real-Time and Embedded Technology  and Applications Symposium, 2016

For better documentation and reproducability, we also keep track of the experiments/benchmarks used in these publications by pursuing the following policy:

* The experiments are collected in the `experiments` folder, which contains subfolders with the names of the publications listed above (e.g. RTAS16).
* These subfolders contain the scripts used for running the experiments and also the reference results in the folder `reference_results`.
* Additionally, we add a tag to the code revision used for producing the results in the corresponding publication.
