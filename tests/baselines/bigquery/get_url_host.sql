safe_cast(

  
    split(
        

  
    split(
        

    replace(
        

    replace(
        

    replace(
        url,
        'android-app://',
        ''
    )


,
        'http://',
        ''
    )


,
        'https://',
        ''
    )


,
        '/'
        )[safe_offset(0)]
  

,
        '?'
        )[safe_offset(0)]
  

 as string)