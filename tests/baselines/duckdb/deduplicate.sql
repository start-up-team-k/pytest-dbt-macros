with row_numbered as (
        select
            _inner.*,
            row_number() over (
                partition by user_id
                order by updated_at desc
            ) as rn
        from my_table as _inner
    )

    select
        distinct data.*
    from my_table as data
    
    natural join row_numbered
    where row_numbered.rn = 1