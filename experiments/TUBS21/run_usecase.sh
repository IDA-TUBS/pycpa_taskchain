#!/bin/bash

mkdir -p results

MODELS=(usecase usecase_pip)
for MODEL in "${MODELS[@]}"; do

	OUT=results/${MODEL}/Uniform
	mkdir -p ${OUT}
	./run.py --name Uniform --outfile ${OUT}/results.csv ./models/${MODEL}.graphml --scheduler SPPSchedulerSegmentsUniform > ${OUT}/output.log

	OUT=results/${MODEL}/CPA
	mkdir -p ${OUT}
	./run.py --name CPA --outfile ${OUT}/results.csv ./models/${MODEL}.graphml --single_task --scheduler pycpa.SPPScheduler > ${OUT}/output.log
done

MODELS=(usecase_pip usecase_pip_block)
for MODEL in "${MODELS[@]}"; do
	OUT=results/${MODEL}/Mixed
	mkdir -p ${OUT}
	./run.py --name Mixed --outfile ${OUT}/results.csv ./models/${MODEL}.graphml --scheduler SPPSchedulerSegmentsInheritance > ${OUT}/output.log

	OUT=results/${MODEL}/EMSOFT17
	mkdir -p ${OUT}
./run.py --name EMSOFT17 --outfile ${OUT}/results.csv ./models/${MODEL}.graphml --scheduler SPPSchedulerInheritance > ${OUT}/output.log
done

MODELS=(usecase usecase_block)
for MODEL in "${MODELS[@]}"; do
	OUT=results/${MODEL}/Mixed
	mkdir -p ${OUT}
	./run.py --name Mixed --outfile ${OUT}/results.csv ./models/${MODEL}.graphml --scheduler SPPSchedulerSegments > ${OUT}/output.log

	OUT=results/${MODEL}/EMSOFT17
	mkdir -p ${OUT}
./run.py --name EMSOFT17 --outfile ${OUT}/results.csv ./models/${MODEL}.graphml --scheduler SPPScheduler > ${OUT}/output.log
done
