if [[ -z "$CONFIG" ]]; then
    python -m exphub.app --galaxy-history-id $HISTORY_ID --host 0.0.0.0 --server timeout=0
else
    python -m exphub.app --config $CONFIG --galaxy-history-id $HISTORY_ID --host 0.0.0.0 --server timeout=0
fi
