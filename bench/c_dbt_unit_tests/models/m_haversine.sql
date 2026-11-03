select round({{ dbt_utils.haversine_distance('lat1', 'lon1', 'lat2', 'lon2') }}, 1) as miles from {{ ref('raw') }}
