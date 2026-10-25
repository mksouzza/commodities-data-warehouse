-- Consolidated analytical model for reporting and BI consumption
with daily_commodities as (
    select
        trade_date,
        symbol,
        commodity_name,
        close_price,
        daily_price_change,
        daily_return_pct,
        moving_avg_7d,
        moving_avg_30d
    from {{ ref('dm_commodities_daily') }}
)

select * from daily_commodities
