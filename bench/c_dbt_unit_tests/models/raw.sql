select
    1 as order_id, 'a' as customer_id, date '2026-01-01' as order_date,
    timestamp '2026-01-01 00:00:00' as start_ts, timestamp '2026-01-01 05:00:00' as end_ts,
    timestamp '2026-01-01 00:00:00' as updated_at,
    cast(0 as double) as lat1, cast(0 as double) as lon1, cast(0 as double) as lat2, cast(0 as double) as lon2
