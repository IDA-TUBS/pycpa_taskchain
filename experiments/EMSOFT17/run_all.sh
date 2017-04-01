RESULT_DIR=results
mkdir $RESULT_DIR

#RUN_CPA='--run_cpa'
#RUN_SYNC='--run_sync'
#RUN_SYNCREF='--run_sync_refined'
#RUN_ASYNC='--run_async'
RUN_CPA=""
RUN_SYNC=""
RUN_SYNCREF=""
RUN_ASYNC=""

########################
# run RTAS experiments #
########################

# synchronous scenario (as chains)
python run_analyses.py --input models/chains_3_3.graphml --print $RUN_CPA $RUN_SYNC $RUN_SYNCREF --run_new --candidate_search --output $RESULT_DIR/chain_3_3.csv --max_iterations 200 --build_chains > $RESULT_DIR/chain_3_3.log

# TODO (optional) run synchronous scenario with mutex blocking

# asynchronous scenario (no chains -> single-task chains)
python run_analyses.py --input models/chains_async_3_3.graphml --print $RUN_CPA --run_new --candidate_search --output $RESULT_DIR/chain_async_3_3-single.csv --max_iterations 200 > $RESULT_DIR/chain_async_3_3-single.log

# asynchronous scenario (as chains)
python run_analyses.py --input models/chains_async_3_3.graphml --print $RUN_CPA $RUN_ASYNC --run_new --candidate_search --output $RESULT_DIR/chain_async_3_3.csv --build_chains --max_iterations 200> $RESULT_DIR/chain_async_3_3.log

# run RTAS use case (no inheritance)
python run_analyses.py --input models/park_assist.graphml --print $RUN_CPA $RUN_SYNC $RUN_SYNCREF --run_new --candidate_search --output $RESULT_DIR/park_assist.csv --build_chains --max_iterations 200 > $RESULT_DIR/park_assist.log

# run RTAS use case with shared service (no inheritance)
python run_analyses.py --input models/park_assist_shared.graphml --print $RUN_CPA --add_mutex_blocking --run_new --candidate_search --output   $RESULT_DIR/park_assist_shared.csv --build_chains --max_iterations 200 > $RESULT_DIR/park_assist_shared.log

# run RTAS use case with shared service and inheritance
python run_analyses.py --input models/park_assist_shared_pip.graphml --print $RUN_CPA --add_mutex_blocking --run_new --candidate_search --output $RESULT_DIR/park_assist_shared_pip.csv --build_chains --max_iterations 200 > $RESULT_DIR/park_assist_shared_pip.log

################
# run use case #
################

python run_analyses.py --input models/combined.graphml --print --run_cpa --run_new --candidate_search --output $RESULT_DIR/combined.csv --calculate_difference --print_differing --build_chains > $RESULT_DIR/combined.log
