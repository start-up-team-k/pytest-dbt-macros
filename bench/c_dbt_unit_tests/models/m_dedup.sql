select order_id, updated_at from (
{{ dbt_utils.deduplicate(ref('raw_dedup'), 'order_id', 'updated_at desc') }}
) as t
