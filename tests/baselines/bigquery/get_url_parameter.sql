nullif(

  
    split(
        

  
    split(
        url,
        'utm_source='
        )[safe_offset(1)]
  

,
        '&'
        )[safe_offset(0)]
  

,'')