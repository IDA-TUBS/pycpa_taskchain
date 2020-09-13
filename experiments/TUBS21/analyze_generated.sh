#!/bin/bash

TIMEOUT=60
MAX_ITER=50

IN=models/generated/noinherit
OUTBASE=results/generated/noinherit
mkdir -p ${OUTBASE}

OUT=${OUTBASE}/CPA
mkdir -p ${OUT}
./run_multiple.py --name CPA --outpath ${OUT} ${IN} --single_task --scheduler pycpa.SPPScheduler --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log

OUT=${OUTBASE}/EMSOFT17
mkdir -p ${OUT}
./run_multiple.py --name EMSOFT17 --outpath ${OUT} ${IN} --scheduler SPPScheduler --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log

OUT=${OUTBASE}/Uniform
mkdir -p ${OUT}
./run_multiple.py --name Uniform --outpath ${OUT} ${IN} --scheduler SPPSchedulerSegmentsUniform --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log

OUT=${OUTBASE}/Mixed
mkdir -p ${OUT}
./run_multiple.py --name Mixed --outpath ${OUT} ${IN} --scheduler SPPSchedulerSegments --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log


IN=models/generated/inherit
OUTBASE=results/generated/inherit
mkdir -p ${OUTBASE}

OUT=${OUTBASE}/CPA
mkdir -p ${OUT}
./run_multiple.py --name CPA --outpath ${OUT} ${IN} --single_task --scheduler pycpa.SPPScheduler --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log

OUT=${OUTBASE}/EMSOFT17
mkdir -p ${OUT}
./run_multiple.py --name EMSOFT17 --outpath ${OUT} ${IN} --scheduler SPPSchedulerInheritance --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log

OUT=${OUTBASE}/Uniform
mkdir -p ${OUT}
./run_multiple.py --name Uniform --outpath ${OUT} ${IN} --scheduler SPPSchedulerSegmentsUniform --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log

OUT=${OUTBASE}/Mixed
mkdir -p ${OUT}
./run_multiple.py --name Mixed --outpath ${OUT} ${IN} --scheduler SPPSchedulerSegmentsInheritance --timeout $TIMEOUT --max_iterations $MAX_ITER > ${OUT}/output.log
