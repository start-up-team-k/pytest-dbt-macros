select cast({{ dbt.dateadd('day', 7, 'order_date') }} as date) as d from {{ ref('raw') }}
