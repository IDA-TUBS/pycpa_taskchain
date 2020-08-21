# Experiment overview

There are two evaluation criteria: accuracy and scalability.

## Accuracy

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


## Scalability

