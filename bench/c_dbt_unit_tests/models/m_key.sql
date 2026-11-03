select {{ dbt_utils.generate_surrogate_key(['order_id', 'customer_id']) }} as k from {{ ref('raw') }}
