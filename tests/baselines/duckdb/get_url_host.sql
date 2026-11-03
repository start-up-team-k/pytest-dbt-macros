
    
    cast(
    string_split(
    string_split(

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


, '/')[ 1 ]
, '?')[ 1 ]
 as TEXT)
