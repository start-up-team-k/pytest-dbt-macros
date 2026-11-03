select {{ dbt.datediff('start_ts', 'end_ts', 'hour') }} as h from {{ ref('raw') }}
