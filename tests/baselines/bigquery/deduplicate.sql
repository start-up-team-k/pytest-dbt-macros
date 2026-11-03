select unique.*
    from (
        select
            array_agg (
                original
                order by updated_at desc
                limit 1
            )[offset(0)] unique
        from my_table original
        group by user_id
    )