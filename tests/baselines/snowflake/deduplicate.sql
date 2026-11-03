select *
    from my_table
    qualify
        row_number() over (
            partition by user_id
            order by updated_at desc
        ) = 1