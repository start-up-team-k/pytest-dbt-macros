{# Macros of the fixture project itself. #}

{# Overrides dbt_utils.safe_divide for every adapter via the dispatch config. #}
{% macro default__safe_divide(numerator, denominator) -%}
    (({{ numerator }}) * 1.0) / nullif(({{ denominator }}), 0)
{%- endmacro %}

{# A project macro with per-adapter branches and a validation error. #}
{% macro to_text(expr) -%}
    {{ return(adapter.dispatch('to_text')(expr)) }}
{%- endmacro %}

{% macro default__to_text(expr) -%}
    cast({{ expr }} as {{ dbt.type_string() }})
{%- endmacro %}

{% macro bigquery__to_text(expr) -%}
    safe_cast({{ expr }} as string)
{%- endmacro %}

{% macro require_positive(n) -%}
    {%- if n <= 0 -%}
        {{ exceptions.raise_compiler_error("n must be positive, got " ~ n) }}
    {%- endif -%}
    {{ n }}
{%- endmacro %}

{% macro tz_expr(col) -%}
    {{ col }} at time zone '{{ var("tz") }}'
{%- endmacro %}
