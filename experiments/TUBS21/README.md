# Experiment overview

There are two evaluation criteria: accuracy and scalability.

## Accuracy

### Description

* four variants of the same use case
	* donation and helping (i.e. perfect priority inheritance)
		* with shared execution contexts: [usecase_pip_block.graphml]
		* without shared execution contexts: [usecase_pip.graphml]
	* arbitrary priorities
		* with shared execution contexts: [usecase_block.graphml]
		* without shared execution contexts: [usecase.graphml]
* five analyses are compared
	* Standard CPA, which is applicable when no blocking is possible, i.e. [usecase.graphml] and [usecase_pip.graphml].
	* The generalised `SPPScheduler` for task chains, which works on all variants.
	* The `SPPSchedulerSegmentsUniform`, which splits the task graph into independent subchains and is applicable to [usecase_pip.graphml] and [usecase.graphml].
	* The `SPPSchedulerSegments`, which supports priority inversion effects and is applicable to [usecase.graphml] and [usecase_block.graphml].
	* The `SPPSchedulerSegmentsInheritance`, which assumes perfect priority inheritance and is thus applicable to [usecase_pip.graphml] and [usecase_pip_block.graphml].

[usecase_pip_block.graphml]: models/usecase_pip_block.graphml
[usecase_pip.graphml]: models/usecase_pip.graphml
[usecase_block.graphml]: models/usecase_block.graphml
[usecase.graphml]: models/usecase.graphml

### Evaluation

* The analyses are run with [run_usecase.sh]. For every analysis, a separate `results.csv` in the corresponding subfolder.
* The python module [usecase.py] is used for combining the individual results into a pandas DataFrame.
* [usecase_stats.py] shows a textual summary of the DataFrame.
* [usecase_boxplot.py] shows boxplots comparing the relative improvement between different analyses.

[run_usecase.sh]: run_usecase.sh
[usecase.py]: eval/usecase.py
[usecase_stats.py]: usecase_stats.py
[usecase_boxplot.py]: usecase_boxplot.py


## Scalability

### Description

* Models are randomly generated with [generate_models.py] with different chain length, chain number, sharing level, branching level, nesting depth, processor utilization and priority assignments.
    * The number of different priority assignments can be provided as an argument.
    * Every model is written to a separate `.graphml` file. The generated models and their parameters are summarized in a `settings.csv`.
* We generate two different sets of models (with and without priority inheritance).
* A particular analysis can be run for a set of models using [run_multiple.py].
* Note, when applying standard CPA or `SPPSchedulerSegmentsUniform` to models with blocking on account of shared execution contexts, the model is relaxed so that blocking is eliminated.

[generate_models.py]: generate_models.py
[run_multiple.py]: run_multiple.py

### Evaluation

* The python module [generated.py] is used for combining the individual results into a pandas DataFrame.
* [generated_stats.py] shows a textual summary of the DataFrame.
* [generated_latbox.py] shows boxplots comparing the relative improvement between different analyses.
* [generated_schedbar.py] shows a barplot with the number of schedulable, unschedulable and timed-out analyses.
* [generated_timebox.py] shows a boxplot with the analysis time for the different analyses.
* [generated_schedgrid.py] shows a grid with the schedulability depending on one or two parameters provided as arguments.

[generated.py]: eval/generated.py
[generated_stats.py]: generated_stats.py
[generated_latbox.py]: generated_latbox.py
[generated_schedbar.py]: generated_schedbar.py
[generated_timebox.py]: generated_timebox.py
[generated_schedgrid.py]: generated_schedgrid.py
