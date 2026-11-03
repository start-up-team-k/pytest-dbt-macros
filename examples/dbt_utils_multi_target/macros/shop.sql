{# A typical project macro: wraps dbt_utils and branches per warehouse. #}
{% macro order_key(customer_id, order_id) -%}
    {{ dbt_utils.generate_surrogate_key([customer_id, order_id]) }}
{%- endmacro %}

{% macro days_since(col) -%}
    {{ return(adapter.dispatch('days_since')(col)) }}
{%- endmacro %}

{% macro default__days_since(col) -%}
    {{ dbt.datediff(col, dbt.current_timestamp(), 'day') }}
{%- endmacro %}

{% macro bigquery__days_since(col) -%}
    date_diff(current_date(), date({{ col }}), day)
{%- endmacro %}
