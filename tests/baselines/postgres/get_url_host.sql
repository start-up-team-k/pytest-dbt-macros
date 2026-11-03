
    
    cast(

  
    

    split_part(
        

  
    

    split_part(
        

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
        '/',
        1
        )


  

,
        '?',
        1
        )


  

 as TEXT)
