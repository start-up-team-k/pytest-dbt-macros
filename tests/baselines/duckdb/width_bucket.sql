
    (
        -- to break ties when the amount is eaxtly at the bucket egde
        case
            when
                mod(
                    
    
    cast(amount as numeric(28,6))
,
                    
    
    cast((( 100 - 0 ) / 10 ) as numeric(28,6))

                ) = 0
            then 1
            else 0
        end
    ) +
      -- Anything over max_value goes the N+1 bucket
    least(
        ceil(
            (amount - 0)/(( 100 - 0 ) / 10 )
        ),
        10 + 1
    )