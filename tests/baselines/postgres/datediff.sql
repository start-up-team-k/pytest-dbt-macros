
        (
        ((end_ts)::date - (start_ts)::date)
     * 24 + date_part('hour', (end_ts)::timestamp) - date_part('hour', (start_ts)::timestamp))
    