select
        distinct on (user_id) *
    from my_table
    order by user_id,updated_at desc