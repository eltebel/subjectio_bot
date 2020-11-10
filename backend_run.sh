export FLASK_ENV=development
# export FLASK_APP=backend.py
export FLASK_DEBUG=1
# export FLASK_RUN_PORT=5000
# export PYTHONPATH=$PYTHONPATH:./botski

# while :; do
    uwsgi --http 0.0.0.0:5000 --py-autoreload=1 \
    --virtualenv ./.venv --honour-stdin \
    --mount /=backend:app 2>&1 |tee -a logs/log_backend.txt
	# flask run -h 0.0.0.0 2>&1 |tee -a logs/log_backend.txt
	# sleep 1
# done
