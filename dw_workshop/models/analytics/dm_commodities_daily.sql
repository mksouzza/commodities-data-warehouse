with market_data as (
    select
        trade_date,
        symbol,
        commodity_name,
        open_price,
        high_price,
        low_price,
        close_price,
        trade_volume
    from {{ ref('stg_commodities') }}
),

windowed_metrics as (
    select
        trade_date,
        symbol,
        commodity_name,
        open_price,
        high_price,
        low_price,
        close_price,
        trade_volume,
        lag(close_price, 1) over (
            partition by symbol order by trade_date
        ) as prev_close_price,
        avg(close_price) over (
            partition by symbol order by trade_date rows between 6 preceding and current row
        ) as moving_avg_7d,
        avg(close_price) over (
            partition by symbol order by trade_date rows between 29 preceding and current row
        ) as moving_avg_30d
    from market_data
),

final_mart as (
    select
        trade_date,
        symbol,
        commodity_name,
        open_price,
        high_price,
        low_price,
        close_price,
        trade_volume,
        prev_close_price,
        round(close_price - prev_close_price, 4) as daily_price_change,
        case
            when prev_close_price is not null and prev_close_price > 0 then
                round(((close_price - prev_close_price) / prev_close_price) * 100, 2)
            else null
        end as daily_return_pct,
        round(moving_avg_7d, 4) as moving_avg_7d,
        round(moving_avg_30d, 4) as moving_avg_30d
    from windowed_metrics
)

select * from final_mart
order by trade_date desc, symbol asc
