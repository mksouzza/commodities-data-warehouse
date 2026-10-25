with trades as (
    select
        transaction_id,
        transaction_date,
        symbol,
        commodity_name,
        action,
        quantity,
        executed_unit_price,
        total_transaction_value,
        broker
    from {{ ref('stg_commodity_transactions') }}
),

market_prices as (
    select
        trade_date,
        symbol,
        close_price as market_close_price
    from {{ ref('stg_commodities') }}
),

joined_trades as (
    select
        t.transaction_id,
        t.transaction_date,
        t.symbol,
        t.commodity_name,
        t.action,
        t.quantity,
        t.executed_unit_price,
        m.market_close_price,
        t.total_transaction_value,
        round(t.executed_unit_price - coalesce(m.market_close_price, t.executed_unit_price), 4) as execution_price_delta,
        t.broker
    from trades t
    left join market_prices m
        on t.transaction_date = m.trade_date
        and t.symbol = m.symbol
)

select * from joined_trades
order by transaction_date desc
